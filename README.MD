# Java Peer Review Training System

An AI-powered educational platform for teaching Java code review skills through interactive practice sessions with real-time feedback and gamification.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## 🎯 Overview

The Java Peer Review Training System is an innovative educational platform designed to help students and developers improve their Java code review skills. The system generates Java code snippets with intentional errors and guides users through the process of identifying and analyzing these issues, providing personalized feedback and tracking progress over time.

### Key Educational Benefits

- **Interactive Learning**: Hands-on practice with real Java code scenarios
- **Immediate Feedback**: AI-powered analysis of review attempts
- **Progressive Difficulty**: Adaptive content based on user skill level
- **Gamification**: Badge system and progress tracking to maintain engagement
- **Multilingual Support**: Available in English and Chinese

## ✨ Features

### Core Functionality

- **Dynamic Code Generation**: AI-generated Java code with configurable error types and difficulty levels
- **Interactive Code Review**: Multi-iteration review process with targeted guidance
- **Real-time Analysis**: LLM-powered evaluation of student review submissions
- **Comprehensive Feedback**: Detailed comparison reports showing identified vs. missed issues

### Educational Features

- **Tutorial System**: Interactive tutorials covering Java error categories
- **Practice Mode**: Focused practice on specific error types
- **Progress Tracking**: Detailed analytics on learning progress
- **Badge System**: Achievement-based gamification with 25+ badges
- **Error Explorer**: Comprehensive database of Java errors organized by category

### Technical Features

- **Streamlit Web Interface**: Modern, responsive web application
- **LangGraph Workflow**: Sophisticated state management for complex educational workflows
- **MySQL Database**: Robust data persistence for user progress and content
- **Groq LLM Integration**: High-performance language model for code generation and analysis
- **Internationalization**: Complete i18n support for multiple languages

## 🛠 Technology Stack

### Backend
- **Python 3.8+**: Core application language
- **LangChain & LangGraph**: LLM orchestration and workflow management
- **Groq API**: Language model provider for code generation and analysis
- **MySQL**: Primary database for user data and content
- **Pydantic**: Data validation and schema management

### Frontend
- **Streamlit**: Web application framework
- **HTML/CSS/JavaScript**: Custom styling and interactions
- **Plotly**: Interactive charts and visualizations

### Infrastructure
- **Docker**: Containerization support
- **Environment Variables**: Secure configuration management
- **Logging**: Comprehensive application monitoring

## 📋 Prerequisites

- Python 3.8 or higher
- MySQL 8.0 or higher
- Groq API key (free at https://console.groq.com/)
- Git for version control

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/java-peer-review-training.git
cd java-peer-review-training
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirement.txt
```

### 4. Database Setup

```bash
# Run the automated database setup
python setup_database.py
```

The setup script will:
- Create the database schema
- Insert initial data (error categories, Java errors, badges)
- Set up user tables and relationships
- Configure proper indexes for performance

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=java_review_db
DB_USER=root
DB_PASSWORD=your_password

# Application Database User
APP_DB_USER=java_review_user
APP_DB_PASSWORD=secure_password

# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_DEFAULT_MODEL=llama3-8b-8192

# Application Settings
LLM_PROVIDER=groq
DEFAULT_LANGUAGE=en
```

### 2. Get Groq API Key

1. Visit https://console.groq.com/
2. Sign up for a free account
3. Generate an API key
4. Add it to your `.env` file

### 3. Database Configuration

The system requires MySQL with proper permissions:

```sql
-- Create application user (if not done by setup script)
CREATE USER 'java_review_user'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER ON java_review_db.* TO 'java_review_user'@'%';
FLUSH PRIVILEGES;
```

## 🎮 Usage

### Starting the Application

```bash
# Run with default settings
python run.py

# Or run directly with Streamlit
streamlit run app.py --server.port 8505
```

The application will be available at `http://localhost:8505`

### User Journey

1. **Registration/Login**: Create an account or log in to track progress
2. **Tutorial**: Learn about Java error categories and review techniques
3. **Practice**: Generate code snippets and practice review skills
4. **Feedback**: Receive detailed analysis and improvement suggestions
5. **Progress**: Track achievements through the badge system

### Admin Features

- **Error Management**: Add new error types and categories
- **User Analytics**: Monitor learning progress across users
- **Content Configuration**: Adjust difficulty levels and error distributions

## 📁 Project Structure

```plaintext
java-peer-review-training/
│
├── backend/                  # Backend source code
│   ├── main.py               # Entry point for the application
│   ├── config.py             # Configuration management
│   ├── database.py           # Database setup and models
│   ├── routes/               # API route handlers
│   ├── services/             # Business logic and services
│   └── utils/                # Utility functions
│
├── frontend/                 # Frontend source code
│   ├── app.py                # Streamlit application
│   ├── components/           # Reusable UI components
│   ├── pages/                # Page layouts and views
│   └── assets/               # Static assets (images, fonts, etc.)
│
├── docs/                     # Documentation files
│   ├── README.md             # Project overview and setup
│   ├── API_DOCS.md           # API documentation
│   └── USER_GUIDE.md         # User guide and tutorials
│
├── tests/                    # Test cases and test data
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
│
├── .env.example              # Example environment variables file
├── .gitignore                # Git ignore file
├── docker-compose.yml        # Docker Compose configuration
└── README.md                 # Project overview and setup instructions
```

## 🗄 Database Schema

```plaintext
java_review_db
│
├── users                     # User information and credentials
│   ├── user_id (PK)          # Unique identifier for each user
│   ├── username               # User's chosen username
│   ├── email                  # User's email address
│   ├── password_hash          # Hashed password for authentication
│   └── created_at            # Account creation timestamp
│
├── roles                     # User roles and permissions
│   ├── role_id (PK)          # Unique identifier for each role
│   ├── role_name              # Name of the role (e.g., admin, user)
│   └── permissions            # Associated permissions for the role
│
├── user_roles                # Mapping of users to roles
│   ├── user_id (FK)          # Reference to the user
│   ├── role_id (FK)          # Reference to the role
│   └── assigned_at           # Timestamp when the role was assigned
│
├── error_categories          # Categories of Java errors
│   ├── category_id (PK)      # Unique identifier for each category
│   ├── category_name          # Name of the category
│   └── description            # Description of the category
│
├── java_errors               # Java errors and solutions
│   ├── error_id (PK)         # Unique identifier for each error
│   ├── category_id (FK)      # Reference to the error category
│   ├── error_snippet          # Code snippet containing the error
│   ├── solution_snippet       # Corrected code snippet
│   └── difficulty_level       # Difficulty level of the error
│
├── badges                    # Achievement badges
│   ├── badge_id (PK)         # Unique identifier for each badge
│   ├── badge_name             # Name of the badge
│   ├── description            # Description of the badge
│   └── criteria               # Criteria to earn the badge
│
└── user_progress             # Tracking user progress and achievements
    ├── progress_id (PK)      # Unique identifier for each progress record
    ├── user_id (FK)          # Reference to the user
    ├── error_id (FK)         # Reference to the Java error
    ├── attempts                # Number of review attempts
    ├── success                 # Whether the error was successfully reviewed
    └── timestamp               # Timestamp of the progress record
```

## 🤝 Contributing

We welcome contributions from developers and educators! To contribute:

1. Fork the repository
2. Create a new branch for your feature or bugfix
3. Make your changes and commit them
4. Push to your fork and submit a pull request

Please ensure your code follows the project's coding standards and includes appropriate tests.

## 🐞 Troubleshooting

- **Database connection issues**: Check your `.env` file for correct database credentials and host settings.
- **API key errors**: Ensure your Groq API key is valid and has the necessary permissions.
- **Dependency issues**: Make sure all Python packages are installed as per the `requirement.txt` file.

For further assistance, please refer to the [GitHub Issues](https://github.com/yourusername/java-peer-review-training/issues) page.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Java Peer Review Training System - Empowering Java Developers Through Interactive Learning