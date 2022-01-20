# Import Libraries
import dataiku
import pandas as pd, numpy as np
from dataiku import pandasutils as pdu
import rasterio
from rasterio import Affine
import os
import geopandas
import matplotlib

def rasters_to_df(folder_name,include_cols=None,transform_raster = None):
    #### Convert a set of rasters as a dataframe. Get latitude and longitude  ####
    
    # Get folder with dataiku api
    folder = dataiku.Folder(folder_name)
    folder_path = folder.get_path()
    # Get list of filenames
    files_name_list = folder.list_paths_in_partition()
    # If only need certain columns, get only those columns
    if include_cols is not None:
        files_name_list = [file for file in file_name_list if file in inlucde_cols]
    # Transform all rasters into one dataframes. Use the file name as the column name and add the suffix _band to indicate the band id
    # The resulting dataframes will have two indexes, correpsonding to the x and y pixels
    image_df_list = [pd.concat([ pd.DataFrame(x).stack() 
                                 for x in rasterio.open(os.path.join(folder_path,tif_path[1:])).read(masked=True)],axis=1)
                      .add_prefix(tif_path[1:len(tif_path)-4]+"_band")
                     for tif_path in files_name_list]
    # Concatenate all dataframes. Add x and y pixels as columns. 
    image_df = pd.concat(image_df_list,axis=1).rename_axis(["x_pixel","y_pixel"]).reset_index(inplace=False)
    
    # To turn the pixel x's and y's into latitude and longitude, we need a transformation functions
    # A raster file will have this transformation. If none is specfied, use the first one listed.
    if transform_raster is None:
        transform_raster_path = os.path.join(folder_path,files_name_list[0][1:])
    else:
        transform_raster_path = os.path.join(folder_path,transform_raster)
    #Get and applly the transformation, save latitude and longitude as new columns the dataframe
    transform = rasterio.open(transform_raster_path).transform
    xs, ys = rasterio.transform.xy(transform=transform,rows= list(image_df['x_pixel']),cols= list(image_df['y_pixel']) )
    image_df['latitude'] = ys
    image_df['longitude'] = xs
    
    return image_df

def save_transform(folder_name,transform_raster,variable_name):
    ### Save a transformation a a project variable ###
    
    # Open file and get the transform.
    folder = dataiku.Folder(folder_name)
    filepath = os.path.join(folder.get_path(),transform_raster)
    transform = rasterio.open(filepath).transform[0:6]
    # Get this project and change project variables. 
    # Project variables can be seen in the 'Variables' section
    proj = dataiku.Project()
    project_variables = proj.get_variables()
    project_variables['standard'][variable_name] = transform
    proj.set_variables(project_variables)


def df_to_raster(output_path,data,transform,include_cols=None):
    if include_cols is None:
        include_cols = [col for col in data.columns if col not in ['x_pixel','y_pixel']]
    data = data.set_index([u'x_pixel',u'y_pixel']).to_panel()[include_cols].values
    output_raster = rasterio.open(output_path,'w',driver="GTiff",
                  count = data.shape[0],
                  height = data.shape[1],
                  width = data.shape[2],
                  transform = transform,
                  dtype= np.double)
    for band in range(1,data.shape[0]):
        output_raster.write(data[band].astype(np.double),band)
    output_raster.close()
