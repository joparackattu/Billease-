# Item detection models

The scanner uses **two** models:

1. **COCO (built-in)** – Detects: apple, banana, orange, bottle, cup, bowl. Loaded automatically.
2. **Trained model (office items)** – Detects: **pen**, mouse, book, keyboard, monitor, etc. **You must add this file yourself.**

## Why isn’t my pen detected?

**Pens and other office items are only detected if the trained model file is present.**

- If **`item_detection.pt`** is **missing** from this folder, only COCO runs → only fruits/common objects (apple, banana, orange, bottle, cup, bowl) are detected. **Pen will not be detected.**
- Place your YOLOv8-trained **`item_detection.pt`** in this folder:  
  `Billease/models/item_detection.pt`  
  (train a model on a dataset that includes a “Pen” class, export as YOLOv8 `.pt`, and put it here.)
- Restart the backend after adding the file.

## Optional: improve pen detection

- Good lighting and the pen centered in the camera view help.
- The app uses a lower confidence threshold for “pen” so smaller or partial detections are still accepted.
