"""Evalscripts for Sentinel Hub processing."""

# NDVI Evalscript
# Calculates Normalized Difference Vegetation Index
NDVI_EVALSCRIPT = """
//VERSION=3

function setup() {
  return {
    input: [{
      bands: [
        "B04",      // Red band
        "B08",      // Near-Infrared band
        "dataMask"  // Sentinel's quality mask
      ],
      units: "DN"   // Digital Numbers (raw values)
    }],
    output: [
      {
        id: "default",
        bands: 1,
        sampleType: "FLOAT32"
      },
      {
        id: "dataMask",
        bands: 1,
        sampleType: "UINT8"
      }
    ]
  };
}

function evaluatePixel(sample) {
  // Exclude invalid pixels (clouds, shadows, no-data)
  if (sample.dataMask === 0) {
    return {
      default: [NaN],
      dataMask: [0]
    };
  }
  
  // Calculate NDVI: (NIR - Red) / (NIR + Red)
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
  
  return {
    default: [ndvi],
    dataMask: [1]
  };
}
""".strip()
