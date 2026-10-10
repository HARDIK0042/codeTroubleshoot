# Run

## Book application

Requires Node.js 22.

```powershell
cd nodejs
npm install
npm run db:init
npm start
```

Open http://localhost:3000

## Handwriting application

Requires Python 3.11 and Tesseract OCR.

Install Tesseract for Windows from https://github.com/UB-Mannheim/tesseract/wiki

The application looks for `C:\Program Files\Tesseract-OCR\tesseract.exe`.

Set `TESSERACT_CMD` to the executable path if Tesseract is installed somewhere else.

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000


1. Node.js Bugs and Fixes

Bug 1: Incorrect Category Filtering
File: src/repositories/bookRepository.js
Before:
category != ?
After:
category = ?
Fix: The filter now returns books belonging to the selected category instead of excluding that category.

Bug 2: Incorrect Book Update Parameters
File: src/controllers/bookController.js
Problem: The price and publication year were passed in the wrong order.
Fix: The parameters were reordered so that published_year and price are passed to their intended fields.

Bug 3: Stock Quantity Increased Instead of Decreased
File: src/services/stockService.js
Before:
Negative adjustments were converted to positive values.
After:
const next = book.quantity + delta;


Fix: The signed adjustment is now applied correctly. For example, reducing stock from 10 by 1 results in 9 rather than 11.

Bug 4: Incorrect Available Copies Count
File: src/repositories/statsRepository.js
Problem: Books with a quantity of 1 or less were not properly included in the total.
Fix: The aggregation now uses SUM(quantity) to calculate the total number of available copies.

Bug 5: Incorrect Search Route Ordering
File: src/routes/books.js
Problem: The /:id route appeared before the /search route, potentially causing search to be interpreted as a book ID.
Fix: The dedicated /search route was moved before /:id.

Bug 6: Outdated Search Results Overwriting New Results
File: frontend/js/app.js
Problem: A slower, older API request could overwrite results from a newer search.
Fix: A booksRequestId mechanism was added to ignore outdated responses.


2. Python OCR Bugs and Fixes

Bug 1: Image Aspect Ratio Distortion
File: app/preprocessing/image_ops.py
Problem: Every image was resized directly to 800 × 600, potentially stretching the image.
Fix: Image proportions are preserved during resizing, and smaller images are not unnecessarily enlarged.

Bug 2: Inefficient OCR Image Preparation
File: app/recognition/ocr.py
Problem: The previous OCR configuration used --psm 7, which is intended for a single text line.
Fix: The image is converted to grayscale and enlarged when necessary. The OCR mode was changed to --psm 11, which is better suited to sparse text layouts.
Note: OCR accuracy should still be evaluated using representative images.

Bug 3: Incorrect Pipeline Argument Order
File: app/services/pipeline.py
Before:
prepare_for_ocr(preprocessed, resized)
After:
prepare_for_ocr(resized, preprocessed)
Fix: The arguments are now passed in the intended order.

Bug 4: Reading a Saved Result Could Truncate the File
File: app/utils/files.py
Before:
open(path, "w+")
After:
open(path, "r")
Fix: The file is opened in read mode, preventing its contents from being erased during a read operation.

Bug 5: Incorrect Text Formatting
File: app/utils/text.py
Problem: Recognized text lines were joined into a single line, making multiline output difficult to read.
Fix: Line breaks are preserved, and a specific text-spacing issue was corrected.

Bug 6: Missing OCR Failure Handling
File: app/routes/recognize.py
Problem: An image with no recognized text could produce an empty result while still returning a successful response.
Fix: Empty OCR output now returns HTTP 422 with guidance to improve image quality. Upload reading was also changed to MAX_BYTES + 1 to help detect files exceeding the configured size limit.

Bug 7: Image Preview Object URLs Were Not Released
File: frontend/static/js/app.js
Problem: Selecting multiple images could leave previous object URLs unreleased.
Fix: URL.revokeObjectURL() is used to release the previous preview URL before creating a new one.

Bug 8: Missing Frontend Error Handling
File: frontend/static/js/app.js
Problem: Network failures and clipboard errors were not handled appropriately.
Fix: try/catch/finally blocks were added to handle failures, display appropriate errors, and restore the processing button's state.