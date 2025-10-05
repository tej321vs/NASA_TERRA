import os
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from sentinelhub import SHConfig, WebFeatureService, BBox, CRS, DataCollection, MimeType, SentinelHubRequest
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. SET UP YOUR SENTINEL HUB CONFIGURATION ---
# IMPORTANT: Replace these with your actual client_id and client_secret
# from your Sentinel Hub Dashboard.
config = SHConfig()
config.sh_client_id = 'YOUR_CLIENT_ID'
config.sh_client_secret = 'YOUR_CLIENT_SECRET'

if not config.sh_client_id or not config.sh_client_secret:
    logging.error("Sentinel Hub client ID and/or secret not configured. Please add them to the script.")
    exit()

def get_ndvi_images_from_sentinelhub(location, start_year, end_year, output_folder):
    """
    Fetches Sentinel-2 data and generates NDVI images for each year.

    Args:
        location (tuple): (longitude, latitude) of the center point.
        start_year (int): The starting year for the time series.
        end_year (int): The ending year for the time series.
        output_folder (str): The directory to save the generated images.
    """
    lon, lat = location
    # Define a bounding box for the study area (e.g., a 10km x 10km area)
    bbox = BBox(bbox=[lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05], crs=CRS.WGS84)

    # Ensure the output directory exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logging.info(f"Created output directory: {output_folder}")

    for year in range(start_year, end_year + 1):
        try:
            logging.info(f"Processing data for the year: {year}")
            
            # --- 2. DEFINE THE DATA REQUEST ---
            # This is a complex request, so we'll break it down.
            # We want to get the median of all images for the summer months.
            evalscript = """
            //VERSION=3
            function setup() {
              return {
                input: [{
                  bands: ["B04", "B08"], // Red and NIR bands for NDVI
                  units: "REFLECTANCE"
                }],
                output: {
                  bands: 1, // We will output a single band (NDVI)
                  sampleType: "FLOAT32"
                }
              };
            }
            function evaluatePixel(sample) {
              let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
              return [ndvi];
            }
            """
            
            # Request data for the summer months of the current year
            time_range = (f'{year}-06-01', f'{year}-09-30')
            
            request = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L1C,
                        time_range=time_range
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response('default', MimeType.TIFF)
                ],
                bbox=bbox,
                size=[512, 512],  # Image size in pixels
                config=config
            )
            
            # --- 3. EXECUTE THE REQUEST AND PROCESS THE DATA ---
            # Get data as a numpy array
            data = request.get_data()
            
            if not data or data[0].size == 0:
                logging.warning(f"No satellite data available for the year {year}. Skipping...")
                continue

            # The downloaded data is a list of arrays. We'll use the first one.
            ndvi_data = data[0].squeeze()

            # --- 4. NORMALIZE AND SAVE THE IMAGE ---
            # Normalize the data for plotting and save as a PNG
            ndvi_min, ndvi_max = np.nanmin(ndvi_data), np.nanmax(ndvi_data)
            if ndvi_max - ndvi_min > 0:
                normalized_ndvi = (ndvi_data - ndvi_min) / (ndvi_max - ndvi_min)
            else:
                normalized_ndvi = np.zeros_like(ndvi_data)

            # Use matplotlib to create an image without borders or axes
            plt.imshow(normalized_ndvi, cmap='viridis')
            plt.title(f'NDVI {year}')
            plt.axis('off')
            plt.savefig(os.path.join(output_folder, f'frame_{year}.png'), bbox_inches='tight', pad_inches=0, dpi=100)
            plt.close()
            
            logging.info(f"Successfully generated image for year {year}.")

        except Exception as e:
            logging.error(f"Error processing year {year}: {e}")
            continue

if __name__ == '__main__':
    # Example: A deforestation-prone area in the Amazon rainforest
    # This is a sample location. You can change it to any coordinates you have.
    amazon_location = (-62.91, -11.66) 
    
    # Define years and output folder
    start_year = 2015 # Sentinel-2 data begins in 2015
    end_year = 2020
    frames_folder = 'deforestation_frames'

    # Run the function to generate the images
    get_ndvi_images_from_sentinelhub(amazon_location, start_year, end_year, frames_folder)