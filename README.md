# AI-Assistant

A simple AI-powered assistant web application that provides context-based conversations, supports multiple chat sessions, and allows document and image-based interactions.

## Project Structure

- **models/base_model.py**  
  - Handles text and document-based queries and generates responses.  
  - Utilizes **LangChain** for context-based conversation and **Groq** API with the **"llama-3.3-70b-versatile"** model.

- **models/image_model.py**  
  - Handles image-based queries and generates responses.  
  - Utilizes **Groq** API with the **"llama-3.2-11b-vision-preview"** model.

- **document_loader.py**  
  - Extracts and processes documents for AI input.  
  - Uses **LangChain** and **Unstructured** for document processing.

- **database.py**  
  - Manages database connections and queries.  
  - Uses **PostgreSQL** as DBMS, **psycopg2** for connection, and **SQLAlchemy** for interaction.

- **auth_service.py**  
  - Implements user authentication and authorization.  
  - Utilizes **FastAPI's security features**.

- **main.py**  
  - Integrates all features and serves APIs using **FastAPI**.