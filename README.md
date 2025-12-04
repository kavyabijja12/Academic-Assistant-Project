# ASU IFT Academic Assistant

An intelligent academic assistant application for the Arizona State University Information Technology (IFT) program that helps students get information about programs, courses, and requirements, and enables them to book appointments with academic advisors.

## Features

### Question & Answer System
- **RAG-powered chatbot** using Retrieval-Augmented Generation
- Answers questions about:
  - Course information and descriptions
  - Program requirements (BS/MS)
  - Application processes
  - Professor and advisor information
- **Hybrid retrieval** combining semantic (FAISS) and keyword (BM25) search
- Response caching for improved performance

### Appointment Booking System
- Interactive booking workflow for student-advisor appointments
- Features:
  - Program-level filtering (Undergraduate/Graduate)
  - Advisor selection
  - Flexible date/time selection
  - Calendar integration
  - Email confirmations
- State machine-based conversational flow

### Authentication & Authorization
- Student authentication with ASU ID
- Admin dashboard access
- Session management
- Secure password hashing

### 📊 Admin Dashboard
- Real-time analytics and statistics
- Message categorization (booking vs questions)
- Question subcategory breakdown
- Recent activity tracking
- User engagement metrics

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit UI (main.py)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼─────────┐
│ Agent Controller │          │  RAG System       │
│                 │          │                   │
│ - Intent        │          │ - Vector Store    │
│   Classification│          │ - Hybrid Retrieval│
│ - Request       │          │ - LLM Generation  │
│   Routing       │          └───────────────────┘
└───────┬────────┘
        │
   ┌────┴────────────────────┐
   │                         │
┌──▼─────────┐      ┌────────▼────────┐
│ Booking    │      │ Authentication  │
│ Agent      │      │ Agent           │
│            │      │                 │
│ - State    │      │ - Student Auth  │
│   Machine  │      │ - Admin Auth    │
│ - Calendar │      └─────────────────┘
│   Service  │
└────────────┘
```

### Technology Stack

- **Frontend**: Streamlit
- **LLM**: Google Gemini (`gemini-2.5-flash`)
- **Embeddings**: SentenceTransformers (`all-MiniLM-L6-v2`)
- **Vector Store**: FAISS
- **Keyword Search**: BM25
- **Database**: SQLite (SQLAlchemy ORM)
- **Authentication**: bcrypt

## Prerequisites

- Python 3.8 or higher
- Google API Key (for Gemini)
- pip package manager

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AcademicAssistant
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

### 4. Initialize the Database

The database will be automatically initialized on first run. To manually initialize:

```bash
python database/init_db.py
```

### 5. Create Admin Account (Optional)

To create an admin account for the dashboard:

```bash
python create_admin.py
```

Default credentials:
- Admin ID: `admin`
- Email: `admin@asu.edu`
- Password: `admin123`

**Change the default password after first login!**

## Running the Application

### Quick Start

Use the provided setup script:

```bash
chmod +x setup_and_run.sh
./setup_and_run.sh
```

### Manual Start

```bash
streamlit run main.py
```

The application will be available at `http://localhost:8501`

## Project Structure

```
AcademicAssistant/
├── main.py                          # Main Streamlit application
├── SimpleUnbiasedRAG.py             # RAG system implementation
├── VectorStore.py                   # Vector store and embeddings
├── requirements.txt                 # Python dependencies
├── setup_and_run.sh                 # Setup and run script
│
├── agents/                          # Agent implementations
│   ├── AgentController.py           # Main routing controller
│   ├── AuthenticationAgent.py       # Authentication logic
│   ├── BookingAgent.py              # Booking operations
│   ├── BookingConversationAgent.py  # Booking conversation flow
│   └── IntentClassifier.py          # Intent classification
│
├── database/                        # Database layer
│   ├── Database.py                  # Database connection
│   ├── models.py                    # SQLAlchemy models
│   ├── init_db.py                   # Database initialization
│   └── appointments.db              # SQLite database (created on first run)
│
├── services/                        # Service layer
│   ├── CalendarService.py           # Calendar and slot management
│   └── EmailService.py              # Email notifications
│
├── vector_store/                    # Vector store files
│   ├── faiss_index_sentence_transformer/  # FAISS index
│   ├── faiss_index_gemini/          # Gemini embeddings index
│   └── bm25_cache.pkl               # BM25 cache
│
├── scrap-clean-chunk/               # Data processing
│   ├── data/                        # Raw data files
│   ├── data_processed/              # Processed data files
│   ├── Scrapper.py                  # Web scraping utilities
│   ├── Cleaner.py                   # Data cleaning
│   └── Chunk.py                     # Text chunking
│
└── Documentation/
    ├── BOOKING_SYSTEM_EXPLANATION.md
    ├── RAG_IMPLEMENTATION_DETAILS.md
    └── LANGCHAIN_AGENT_IMPACT_ANALYSIS.md
```

## Configuration

### Database Setup

The application uses SQLite databases:

- `database/appointments.db` - Appointments, students, advisors, calendars
- `chat_history.db` - Chat history and user sessions

These are created automatically on first run.

### Vector Store

The vector store indexes are pre-built and stored in `vector_store/`. To rebuild:

1. Process data in `scrap-clean-chunk/`
2. Run the indexing script (if available)
3. Update vector store paths in `VectorStore.py`

## Usage

### For Students

1. **Login**: Click "Login" in the sidebar and enter your ASU ID and password
2. **Ask Questions**: Type questions about programs, courses, or requirements
3. **Book Appointments**: Click "Book Appointment" to start the booking process
4. **View History**: Check chat history in the sidebar

### For Admins

1. **Login**: Click "Admin Login" in the sidebar
2. **View Dashboard**: Access analytics and statistics
3. **Monitor Activity**: Track user queries and booking requests

## Key Features Explained

### RAG System

- **Hybrid Retrieval**: Combines semantic (FAISS) and keyword (BM25) search
- **Smart Caching**: Caches responses to reduce API calls
- **Source Attribution**: Shows document sources for answers

### Booking System

- **State Machine**: Manages multi-step booking conversation
- **Flexible Scheduling**: Handles specific dates, date ranges, and time preferences
- **Validation**: Ensures valid dates, times, and availability

### Intent Classification

- **Fast Keyword Matching**: Quick classification for common patterns
- **LLM Fallback**: Uses Gemini for ambiguous cases
- **Hierarchical Categories**: Organizes questions into subcategories

## API Costs Optimization

The system minimizes LLM API calls:

- **Local Embeddings**: Uses SentenceTransformers (no API calls)
- **Response Caching**: Caches frequent queries
- **Keyword-based Classification**: Most intents detected without LLM
- **Typical Usage**: 1-2 LLM calls per query

See `RAG_IMPLEMENTATION_DETAILS.md` for detailed cost analysis.

## Troubleshooting

### Application Won't Start

- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify `.env` file exists with `GOOGLE_API_KEY`
- Ensure Python 3.8+ is being used

### Database Errors

- Delete existing database files and restart (they will be recreated)
- Check file permissions in the `database/` directory

### Vector Store Issues

- Verify vector store files exist in `vector_store/`
- Check that FAISS index files are not corrupted

### API Key Errors

- Verify `GOOGLE_API_KEY` is set in `.env`
- Check API key is valid and has proper permissions

## Development

### Adding New Features

- **New Questions**: Add documents to `scrap-clean-chunk/data/` and rebuild index
- **Booking Enhancements**: Modify `BookingConversationAgent.py`
- **New Intents**: Update `IntentClassifier.py`

### Testing

Run the application locally and test:
- Student authentication
- Question answering
- Booking flow
- Admin dashboard

## License

This project is developed for ASU Polytechnic School - Information Technology Program.

## Support

For issues or questions, please contact the development team or refer to the detailed documentation in the project's markdown files.

---

**ASU Polytechnic School - Information Technology Program**  
Academic Assistant v1.0

