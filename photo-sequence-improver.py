# %%
from PIL import Image
from PIL.ExifTags import TAGS
import pandas as pd
import os
from tqdm import tqdm
import math
import folium

# settings
directory = 'C:/path/to/my_sequence'
min_dist = 5 # in m
show_info = True # if True, creates some graphic evaluation
delete_files = True # if False, script just calculates the pictures that need to be deleted but don't delete one

# set earth radiu in km
earth_radius = 6369 
# initialize empty df
df = pd.DataFrame(columns = ['name', 'time', 'lon', 'lat'])
# initialize delete df
del_df = pd.DataFrame(columns = ['name', 'time', 'lon', 'lat'])
# initialize loop-condition
pics_under_min = 1

def prepare_exif_loop(directory, df):
    """loop through given directoy of photo sequence to read exif data

    Args:
        directory (str): full path to photo sequence
        df (dataframe): name, time, position of photos in sequence

    Returns:
        df: name, time, position of photos in sequence
    """    
    # list of all filenames in directory
    all_files = os.listdir(directory)

    # get exif data and write it to df
    for filename in tqdm(all_files):
        fullpath = directory + '\\' + filename 
        exif = get_exif(fullpath)

        time = exif['DateTime']
        lon = convert_to_degress(exif['GPSInfo'][2])
        lat = convert_to_degress(exif['GPSInfo'][4])

        # create merge_df with new exif data from current picture
        merge_df = pd.DataFrame({'name': [filename],
                    'time': [time],
                    'lon': [lon],
                    'lat': [lat]})
        # append merge_df to final df
        df = df.append(merge_df, ignore_index=True)
    return df

def get_exif(filename):
    """extract exif-data of given picture

    Args:
        filename (str): filepath

    Returns:
        dict: contains exif-data
    """    
    ret = {}
    img = Image.open(filename)
    info = img._getexif()
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret[decoded] = value
    return ret

def convert_to_degress(coordinate):
    """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format

    Args:
        coordinate (list): lon or lat as list that contains degrees, minutes, seconds

    Returns:
        float: lon or lat as float
    """    
    return coordinate[0] + (coordinate[1] / 60.0) + (coordinate[2] / 3600.0)

def get_distance(lat_1, lng_1, lat_2, lng_2): 
    """calculates the distance between two coordinates

    Args:
        lat_1 (float): start latitude
        lng_1 (float): start longitude
        lat_2 (float): end latitude
        lng_2 (float): end longitude

    Returns:
        float: distance in meter
    """    
    # transform coordinates to radians
    lat_1, lng_1, lat_2, lng_2 = map(math.radians, [lat_1, lng_1, lat_2, lng_2])

    # calculate the distance
    d_lat = lat_2 - lat_1
    d_lng = lng_2 - lng_1 

    temp = (  
         math.sin(d_lat / 2) ** 2 
       + math.cos(lat_1) 
       * math.cos(lat_2) 
       * math.sin(d_lng / 2) ** 2
    )

    return 6373.0 * 1000 * (2 * math.atan2(math.sqrt(temp), math.sqrt(1 - temp)))

def optional_track_infos(df, del_df, original_df):
    """provides some optional infos about process

    Args:
        df (dataframe): name, time, position of photos in sequence
        del_df (dataframe): name, time, position of photos in sequence to be deleted as they are too close to predecessor
        original_df (dataframe): name, time, position of photos in sequence as they were read out of exif data at beginning
    """    
    # distance plot
    df['distance'].iloc[2:].plot()

    # hist plot
    df.iloc[2:].hist(column='distance')

    # how much pics were deleted (if set to True)
    print(str(len(del_df.index)) + ' of ' + str(len(original_df.index)) + ' were deleted (if delete_files set to True.')

    # plot map with track
    # calc list of trackpoints
    def coord_list_from_dataframe(df, points):
        for coord in range(len(df.index)):
            new_point = [(df['lon'].iloc[coord]), df['lat'].iloc[coord]]
            points.append(new_point)
        return points

    points = [] # points of track of pics to be uploaded
    points = coord_list_from_dataframe(df, points)
    points = points[0::(int(.05*len(df.index)))] # reduce list (performance)

    deleted_pics = [] # points of deleted pics
    deleted_pics = coord_list_from_dataframe(del_df, deleted_pics)
    
    #initialize map for track
    track_map = folium.Map(location=[20,0], zoom_start=2)
    # plot track on map
    for coord in tqdm(range(len(df.index))):
        folium.PolyLine(points).add_to(track_map)
    print('safeing map 1 ...')
    # safe map
    track_map.save('track.html')
    print('map 1 safed')

    #initialize map for deleted pics
    del_map = folium.Map(location=[20,0], tiles="OpenStreetMap", zoom_start=2)
    # plot points on map
    for i in tqdm(range(0,len(del_df))):
        folium.Marker(location=[del_df.iloc[i]['lon'], del_df.iloc[i]['lat']]).add_to(del_map)
    print('safeing map 2 ...')
    # safe map
    del_map.save('deleted_pics.html')
    print('map 2 safed')

def calc_distances(df):
    """calculates distances between following coordinates in df"""

    # initialize the list of distances
    dist_list =[9999]

    # calculate distance between points
    for i in range(len(df.index)-1):
        # set start- and end-values for each calculation
        start_lon = df['lon'].iloc[i]
        start_lat = df['lat'].iloc[i]
        end_lon = df['lon'].iloc[i+1]
        end_lat = df['lat'].iloc[i+1]

        # calculate the distance in meter
        distance = get_distance(start_lon, start_lat, end_lon, end_lat)

        # append current distance
        dist_list.append(distance)

    # append dist_list to df
    df['distance'] = dist_list

    return(df)

# get df with exif data
df = prepare_exif_loop(directory, df)

# safe original df for further evaluations
original_df = df

# loop as long there are pics closer than min_dist
while pics_under_min != 0:
    # calculate distances between following points in df
    df = calc_distances(df)

    # cut pics/rows that are too close from df and copy it to del_df
    for row in range(len(df.index)):
        if df['distance'].iloc[row] < min_dist:
            del_df = del_df.append(df.iloc[row], ignore_index=True)
            df.drop(row, inplace=True)
            df = df.reset_index(drop=True)
            break

    # current number of pics under min distance
    pics_under_min = len(df[(df['distance'] < min_dist)])

    print(pics_under_min)

del_files = del_df['name'].tolist()

# delete files
if delete_files == True:
    del_files = del_df['name'].tolist()
    if del_files == []:
        print('No files need to be deleted!')
    else:
        for filename in del_files:
            os.remove(directory + '\\' + filename)

# optional track-information
if show_info == True:
    optional_track_infos(df, del_df, original_df)

print('\nfinish')
