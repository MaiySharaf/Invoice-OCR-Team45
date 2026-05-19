# Invoice-OCR-Team45
# 📖 **InvoiceIQ - Complete Project README**

---

##  **Project Overview**

**InvoiceIQ** is an intelligent document processing system that automatically extracts structured information (company name, invoice number, date, total amount, tax) from uploaded invoice and receipt images or PDFs using **OCR (Tesseract)** and **NLP (spaCy)** technologies.

---

##  **Problem Statement**

Many businesses and individuals handle large numbers of invoices and receipts manually, which is time consuming and error prone. Extracting key information such as company name, date, and total amount from these documents requires reading and manual entry.

---

##  **Solution**

InvoiceIQ automates this process by building a system that extracts structured information from invoices and receipt documents using OCR and NLP techniques. Users can upload documents, and the system extracts key fields in seconds.

---

##  **Target Users**

- Small business owners who need to track expenses and invoices
- Accountants processing multiple financial documents daily
- Administrative staff in finance departments
- Freelancers managing client invoices

---

##  **Key Features**

- Upload invoices and receipts (JPG, PNG, PDF formats)
- OCR text extraction with image preprocessing for better accuracy
- NLP-based structured field extraction using custom spaCy NER model
- Baseline (Regex) vs Improved (NLP) comparison side-by-side
- Async SQS queue processing for non-blocking operations
- Dead Letter Queue for failed documents with automatic 3 retries
- Stage-by-stage processing history for full traceability
- CloudWatch logging and monitoring for all events
- Secure AWS S3 storage for uploaded files
- Modern web dashboard with interactive Plotly charts
- Docker containerization ready for consistent deployment

---

##  **System Architecture**

The system follows a cloud-native architecture:

**User Flow:**
1. User uploads document through web interface
2. Document stored in AWS S3 bucket
3. Document reference sent to AWS SQS queue for async processing
4. SQS consumer picks up message and processes document
5. OCR extracts text using Tesseract
6. NLP model extracts structured fields using spaCy
7. Results saved to database and displayed to user
8. If processing fails after 3 retries, message moves to SQS Dead Letter Queue

**Components:**
- Frontend: HTML/CSS/JS served via Nginx
- Backend: Flask REST API running on EC2
- Database: SQLite for metadata storage
- Queue: AWS SQS for async processing
- Storage: AWS S3 for document persistence
- Monitoring: AWS CloudWatch for logs
- Security: AWS IAM roles 

---

##  **Technology Stack**

**Backend:**
- Python 3.10+ as main programming language
- Flask framework for REST API development
- Gunicorn as production WSGI server
- SQLite for local database storage

**Frontend:**
- HTML5, CSS3, JavaScript for UI
- Plotly.js for interactive charts
- Custom CSS with modern dark theme

**AI & NLP:**
- Tesseract OCR 5.x for text extraction from images
- Pillow (PIL) for image preprocessing (grayscale, sharpen, contrast)
- spaCy 3.x for Named Entity Recognition
- Custom NER model trained on invoice data (en_core_web_sm based)
- pdf2image for PDF to image conversion

**Cloud Services (AWS):**
- EC2 (t3.micro, Ubuntu 22.04) for hosting backend and frontend
- S3 (invoice-ocr-uploads-team45) for secure file storage
- SQS (invoice-processing-queue) for async document processing
- SQS DLQ (invoice-dlq) for failed messages with 3 retry policy
- CloudWatch (/invoice-ocr/backend) for centralized logging
- IAM (invoice-ec2-role) for security permissions
- ECR (invoiceiq:latest) for Docker container registry

**Deployment & DevOps:**
- Docker for containerization
- Nginx as reverse proxy for frontend
- systemd for consumer service auto-restart
- Git and GitHub for version control

---

## 📊 **Model Performance Results**

**Baseline (Regex) - Macro F1 Score: 72%**

Per-field performance:
- Invoice Number: 74% F1
- Invoice Date: 79% F1
- Seller Name: 64% F1
- Client Name: 67% F1
- Total Amount: 80% F1

**Improved (spaCy NER) - Macro F1 Score: 94%**

Per-field performance:
- Invoice Number: 94% F1
- Invoice Date: 95% F1
- Seller Name: 91% F1
- Client Name: 92% F1
- Total Amount: 96% F1

**Overall Performance Improvement: +22%**

---

##  **API Endpoints**

The system exposes 10 REST API endpoints:

- **GET /health** - Service health check (returns status, S3 status, NLP loaded)
- **GET /model/version** - Get model version and F1 scores
- **GET /metrics** - System metrics (total requests, average latency)
- **POST /upload** - Upload document (supports both sync and async SQS modes)
- **GET /history** - List all processed documents
- **GET /record/{id}** - Get specific document extraction results
- **GET /processing/history/{id}** - Stage-by-stage processing traceability
- **GET /dlq/sqs** - Get SQS Dead Letter Queue message count
- **POST /dlq/sqs/retry/{id}** - Retry a specific failed document from DLQ
- **GET /evaluate** - Run model evaluation comparing Baseline vs Improved F1 scores

---

##  **Cloud Requirements Checklist**

| Requirement | Status | How It's Implemented |
|-------------|--------|----------------------|
| Host inference as API |  Complete | Flask backend running on EC2 port 5000 |
| Store uploaded files safely |  Complete | S3 bucket with public access blocked and SSE encryption |
| Model version management |  Complete | /model/version endpoint returns version and F1 scores |
| Monitor latency/errors |  Complete | /metrics endpoint tracks requests and latency + CloudWatch logs |
| IAM/Security |  Complete | invoice-ec2-role attached to EC2, no hardcoded credentials |
| Online inference statement |  Complete | All responses include "inference_type": "online" |
| Docker containerization |  Complete | Dockerfile in GitHub, image pushed to AWS ECR |

---

##  **Bonus Features (Cloud Fault-Tolerant Pipeline)**

| Feature | Description |
|---------|-------------|
| Dead Letter Queue | SQS DLQ captures failed documents after 3 automatic retries |
| Automatic Retries | SQS redrive policy configured for 3 attempts before moving to DLQ |
| Processing History | Stage-by-stage traceability via /processing/history endpoint |
| Async Processing | SQS queue enables non-blocking document processing |
| CloudWatch Logging | Centralized logging for all application events with 30-day retention |
| Docker Containerization | Complete Dockerfile + ECR image for consistent deployment anywhere |

---

##  **Live Deployment**

**Frontend URL:** http://13.50.154.60/ 

**Access:** Login with password `invoice2026`

**Quick Links:**
- Health Check: http://13.50.154.60/api/health
- Model Version: http://13.50.154.60/api/model/version
- Metrics: http://13.50.154.60/api/metrics
---

##  **Demo Flow (10 Steps)**

1. User opens the system web interface
2. User logs in with password "invoice2026"
3. User uploads an invoice or receipt file (JPG, PNG, or PDF)
4. System stores the file in AWS S3 bucket
5. Document reference sent to SQS queue for async processing
6. OCR extracts raw text from the document using Tesseract
7. NLP model processes text and extracts structured fields using spaCy
8. Results are saved to database and displayed on dashboard
9. User views Baseline (Regex) vs Improved (NLP) comparison side-by-side
10. If processing fails after 3 retries, message goes to SQS DLQ for manual retry

---

##  **Testing the System**

**What to Test:**
- Upload a valid invoice image → Should extract all fields correctly
- Upload a corrupted image → Should go to Dead Letter Queue after 3 retries
- Upload a photo (non-invoice) → Should go to Dead Letter Queue
- Check History tab → Shows all previously processed documents
- Check Metrics tab → Shows system statistics and DLQ count
- Run Evaluation → Shows F1 score comparison chart

**Expected Results:**
- Valid invoice: 94% accuracy with improved NLP model
- Failed documents: Appear in DLQ with "Processing failed after 3 retries"
- Processing history: Shows each stage (upload → S3 → SQS → OCR → NLP → save)

---

##  **Project Structure**

```
invoice-ocr-system/
├── backend/           # Flask API, OCR engine, NLP model, SQS consumer
├── frontend/          # HTML, CSS, JavaScript dashboard
├── data/              # Dataset images, labels, SQLite database
├── models/            # Trained spaCy NER model
├── artifacts/         # OCR cache for faster processing
├── reports/           # Generated documentation
├── Dockerfile         # Container configuration
└── README.md          # This documentation
```

---

##  **Prerequisites for Local Development**

- Python 3.10 or higher
- Tesseract OCR installed on system
- Poppler installed for PDF processing
- AWS account (for cloud deployment)
- Docker Desktop (optional, for containerization)

---

##  **Deployment Summary**

The system is fully deployed on AWS with:

**Compute:** EC2 t3.micro running Ubuntu 22.04
**Storage:** S3 bucket for uploaded files, SQLite for metadata
**Messaging:** SQS queue for async processing with DLQ for failures
**Monitoring:** CloudWatch logs with 30-day retention
**Security:** IAM role with least privilege (no hardcoded keys)
**Container:** Docker image available in AWS ECR
**Frontend:** Nginx serving static files on port 80
**Backend:** Flask with Gunicorn on port 5000

---

##  **Achievements**

-  94% F1 score using custom spaCy NER model
-  +22% improvement over baseline regex approach
-  Complete fault-tolerant pipeline with SQS and DLQ
-  Full processing history traceability
-  Production-ready AWS deployment
-  Docker containerization ready

---

## 👨‍💻 **Authors**

**Team 45 - Cloud Computing Spring 2026**

- مي ناصر امين (20230606) - Cloud Deployment Lead
- مهند عبدالمؤمن اسماعيل (20230599) - evaluations/data
- نور محمد هيثم (20230630) - AI / NLP Extraction Lead
- ايفان هاني سمير (20230107) - AI / OCR & Text Processing
- ادهم فوزي حمدي (20220054) - Frontend Developer
- اياد طه عبدالفتاح (20220086) - Backend
---

## 🙏 **Acknowledgments**

- Course instructors for guidance and resources
- Teaching assistants for technical support
- AWS for free tier services enabling cloud deployment
- spaCy team for NLP framework
- Tesseract team for OCR engine

---

## 📄 **Conclusion**

InvoiceIQ successfully demonstrates a complete end-to-end document intelligence system deployed on AWS cloud infrastructure. The system achieves 94% F1 score using a custom spaCy NER model, compared to 72% with baseline regex extraction. The cloud deployment includes EC2 hosting, S3 storage, SQS asynchronous processing with Dead Letter Queue (3 retries), CloudWatch logging, and IAM security. All bonus requirements for fault-tolerant pipeline, processing history traceability, and retry mechanisms are fully implemented. The system is ready for production use and can be scaled horizontally by adding more consumer instances behind the SQS queue.

---

**© 2026 Team 45 - All Rights Reserved**
