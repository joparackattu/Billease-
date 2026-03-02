# Dataset Structure for BILLESE Object Detection

This directory contains the training dataset for the YOLOv8 object detection model.

## 📁 Directory Structure

```
datasets/
├── train/
│   ├── images/          # Training images
│   │   ├── tomato_001.jpg
│   │   ├── tomato_002.jpg
│   │   ├── potato_001.jpg
│   │   └── ...
│   └── labels/          # YOLO format labels
│       ├── tomato_001.txt
│       ├── tomato_002.txt
│       ├── potato_001.txt
│       └── ...
├── val/                 # Validation set (optional but recommended)
│   ├── images/
│   └── labels/
└── data.yaml            # Dataset configuration (auto-generated)
```

## 🏷️ Label Format (YOLO)

Each image needs a corresponding `.txt` file with the same name.

**Format:** `class_id center_x center_y width height`

All values are normalized (0-1):
- `class_id`: Integer class ID (0=tomato, 1=potato, etc.)
- `center_x`: X coordinate of bounding box center (0-1)
- `center_y`: Y coordinate of bounding box center (0-1)
- `width`: Width of bounding box (0-1)
- `height`: Height of bounding box (0-1)

**Example (tomato_001.txt):**
```
0 0.5 0.5 0.3 0.3
```
This means: class 0 (tomato) at center of image, 30% width and height.

## 📝 How to Create Labels

### Option 1: Use LabelImg (Recommended for beginners)

1. **Install LabelImg:**
   ```bash
   pip install labelimg
   ```

2. **Open LabelImg:**
   ```bash
   labelimg
   ```

3. **Setup:**
   - Click "Open Dir" → Select `datasets/train/images`
   - Click "Change Save Dir" → Select `datasets/train/labels`
   - Select "YOLO" format (bottom right)
   - Create classes: tomato, potato, onion, carrot, cabbage

4. **Label images:**
   - Draw bounding boxes around items
   - Assign class labels
   - Save (Ctrl+S) - creates .txt file automatically

### Option 2: Use Roboflow (Online, Free)

1. Go to [roboflow.com](https://roboflow.com)
2. Create account and new project
3. Upload images and label them online
4. Export in YOLO format
5. Download and extract to `datasets/` folder

### Option 3: Use CVAT (Advanced)

For larger datasets, use [CVAT](https://cvat.org/)

## 📊 Recommended Dataset Size

- **Minimum:** 50-100 images per class
- **Good:** 200-500 images per class
- **Excellent:** 1000+ images per class

**For college demo:** 50-100 images per item is sufficient!

## 🎯 Classes for BILLESE

Default classes:
- `0`: tomato
- `1`: potato
- `2`: onion
- `3`: carrot
- `4`: cabbage

You can add more classes in `data.yaml` after training.

## 🚀 Quick Start

1. **Collect images:**
   - Take photos of items with your camera
   - Or download from internet (ensure you have rights)
   - Save to `datasets/train/images/`

2. **Label images:**
   - Use LabelImg to create bounding boxes
   - Labels saved to `datasets/train/labels/`

3. **Split dataset:**
   - Move 20% of images to `datasets/val/` for validation
   - Keep 80% in `datasets/train/`

4. **Train model:**
   ```bash
   python train_model.py
   ```

## 💡 Tips

- **Variety is key:** Include different lighting, angles, backgrounds
- **Quality over quantity:** Better to have 50 good images than 200 bad ones
- **Balance classes:** Try to have similar number of images per class
- **Test images:** Keep some images separate for final testing (not in train/val)

## 📚 Resources

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [LabelImg Tutorial](https://github.com/tzutalin/labelImg)
- [YOLO Label Format](https://docs.ultralytics.com/datasets/)
















