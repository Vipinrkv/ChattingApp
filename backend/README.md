# ChattingApp Backend

> Note: This README documents the Python backend and explains how the FastAPI server connects to Firebase auth, the database, and the frontend API client.
>
> Use this file when configuring backend services, running migrations, or debugging API integration.

A comprehensive, secure backend for a chat and social platform built with FastAPI, PostgreSQL, and Firebase authentication.

## Deep Reference Docs

- [Database and backend details](../docs/DATABASE_BACKEND_DETAILS.md): complete table map, model/service/route usage, endpoint summary, and backend techniques.
- [Full connection structure](../docs/CONNECTION_STRUCTURE.md): frontend-to-backend-to-database connection flow, auth flow, API client behavior, and realtime flow.
- [File structure and system flow](../docs/FILE_STRUCTURE_AND_SYSTEM_FLOW.md): file layout and click-by-click UI/backend/database behavior.

## Project Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py          # Application configuration and settings
│   │   ├── firebase.py        # Firebase authentication initialization and utilities
│   │   └── security.py        # Encryption, JWT, and security utilities
│   ├── database/
│   │   └── connection.py      # Async PostgreSQL connection and session management
│   ├── models/
│   │   ├── user.py            # User model with relationships
│   │   ├── friend.py          # Friend request model
│   │   ├── follower.py        # Follow/follower relationships
│   │   ├── block.py           # User blocking functionality
│   │   ├── message.py         # Direct messages between users
│   │   ├── post.py            # Social media posts with visibility controls
│   │   ├── group.py           # Group chat rooms
│   │   ├── group_member.py    # Group membership management
│   │   ├── group_message.py   # Messages within groups
│   │   ├── group_post.py      # Posts within groups
│   │   └── chat_settings.py   # Chat preferences (mute, archive)
│   ├── routes/
│   │   ├── user_routes.py     # User registration, profile management
│   │   ├── friend_routes.py   # Friend request management
│   │   ├── follow_routes.py   # Follow/unfollow functionality
│   │   ├── block_routes.py    # User blocking/unblocking
│   │   ├── chat_routes.py     # Direct messaging endpoints
│   │   ├── group_routes.py    # Group creation and management
│   │   └── post_routes.py     # Post creation, feed, and social features
│   ├── schemas/
│   │   ├── user.py            # User data validation schemas
│   │   ├── friend_schema.py   # Friend request schemas
│   │   ├── group_schema.py    # Group management schemas
│   │   ├── message_schema.py  # Message and chat schemas
│   │   └── post_schema.py     # Post and feed schemas
│   ├── services/
│   │   ├── user_service.py    # User CRUD operations
│   │   ├── friend_service.py  # Friend request logic
│   │   ├── follow_service.py  # Follow/follower operations
│   │   ├── block_service.py   # Blocking functionality
│   │   ├── chat_service.py    # Direct messaging logic
│   │   ├── group_service.py   # Group management operations
│   │   ├── post_service.py    # Post CRUD operations
│   │   ├── feed_service.py    # Personalized feed generation
│   │   ├── group_feed_service.py # Group post management
│   │   └── privacy.py         # Content visibility and privacy rules
│   ├── utils/
│   │   └── privacy.py         # Privacy and permission utilities
│   ├── websocket/
│   │   ├── chat_socket.py     # Real-time direct messaging
│   │   └── group_socket.py    # Real-time group chat
│   └── main.py                # FastAPI application setup and routing
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
└── venv/                      # Python virtual environment
```

## Features

### Authentication & Security

- Firebase Authentication integration
- JWT token-based API authentication
- AES-256 encryption for sensitive data
- Secure password hashing with bcrypt
- Improved Firebase token verification logging and basic suspicious auth attempt warnings

### User Management

- User registration and profile management
- Friend requests and relationships
- Follow/follower system
- User blocking functionality

### Social Features

- Posts with privacy controls (public, friends-only, followers-only)
- Personalized feed generation
- Like and interaction system (extensible)

### Chat & Communication

- Real-time direct messaging via WebSocket
- Group chat functionality
- Message encryption and privacy controls
- Chat settings (mute, archive)

### Group Management

- Public, private, and anonymous groups
- Group membership and role management
- Group posts and discussions
- Invitation system

## Technology Stack

- **Backend Framework**: FastAPI (async Python web framework)
- **Database**: PostgreSQL with asyncpg driver
- **ORM**: SQLAlchemy 2.0 (async support)
- **Authentication**: Firebase Admin SDK
- **Real-time**: WebSocket support
- **Security**: AES encryption, JWT tokens, bcrypt hashing
- **Validation**: Pydantic schemas
- **Deployment**: Uvicorn ASGI server

## API Endpoints

### Users

- `POST /api/v1/users/register` - Register new user
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/{user_id}` - Update user profile
- `GET /api/v1/users/{user_id}` - Get user by ID

### Friends

- `POST /api/v1/friends/requests/{addressee_id}` - Send friend request
- `POST /api/v1/friends/requests/{request_id}/respond` - Respond to friend request
- `GET /api/v1/friends` - Get friends list
- `GET /api/v1/friends/requests` - Get pending friend requests

### Follows

- `POST /api/v1/follows/{following_id}` - Follow user
- `DELETE /api/v1/follows/{following_id}` - Unfollow user
- `GET /api/v1/follows/following` - Get users you follow
- `GET /api/v1/follows/followers` - Get your followers

### Blocks

- `POST /api/v1/blocks/{blocked_id}` - Block user
- `DELETE /api/v1/blocks/{blocked_id}` - Unblock user

### Posts

- `POST /api/v1/posts/create` - Create new post
- `GET /api/v1/posts/{post_id}` - Get post by ID
- `PUT /api/v1/posts/{post_id}` - Update post
- `DELETE /api/v1/posts/{post_id}` - Delete post
- `GET /api/v1/posts/user/{user_id}` - Get user's posts
- `GET /api/v1/posts/feed/{user_id}` - Get personalized feed

### Group Posts

- `POST /api/v1/posts/group/{group_id}/create` - Create group post
- `GET /api/v1/posts/group/{group_id}/feed` - Get group feed
- `DELETE /api/v1/posts/group/{post_id}` - Delete group post

### Chat

- `POST /api/v1/chat/{receiver_id}/messages` - Send direct message
- `GET /api/v1/chat/{peer_id}/messages` - Get conversation
- `PATCH /api/v1/chat/{peer_id}/settings` - Update chat settings

### Groups

- `POST /api/v1/groups` - Create new group
- `POST /api/v1/groups/{group_id}/join` - Join group
- `POST /api/v1/groups/{group_id}/leave` - Leave group
- `POST /api/v1/groups/{group_id}/invite` - Invite user to group
- `GET /api/v1/groups/{group_id}/members` - Get group members
- `POST /api/v1/groups/{group_id}/messages` - Send group message
- `GET /api/v1/groups/{group_id}/messages` - Get group messages

### WebSocket Endpoints

- `WS /ws/chat/{peer_id}` - Real-time direct messaging
- `WS /ws/groups/{group_id}` - Real-time group chat

## Setup & Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Firebase project with authentication enabled

### Environment Setup

1. **Clone and navigate to backend directory:**

   ```bash
   cd backend
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**

   ```bash
   # Windows
   venv\Scripts\activate
   ```

4. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

5. **Copy the environment example:**

   ```bash
   copy .env.example .env
   ```

6. **Set `APP_ENV` to `production` for production deployments and ensure all required values are configured.**

7. **Optional: use `ENV_FILE` to load a different env file:**

   ```bash
   set ENV_FILE=.env.production
   ```

   This allows you to keep separate configuration files, e.g. `.env.development`, `.env.staging`, and `.env.production`.

### Alembic Migrations

The backend now uses Alembic for database schema migrations instead of automatic table creation.

- Generate a new migration after changing models:

  ```bash
  alembic revision --autogenerate -m "describe change"
  ```

- Apply the latest migrations:

  ```bash
  alembic upgrade head
  ```

- Use the new helper to create a timestamped backup before migration and coordinate execution with Redis when available:

  ```bash
  python backend/tools/db_backup_and_migrate.py --database-url "$DATABASE_URL" --backup-dir "./backups"
  ```

- If you run Alembic from outside the backend folder, specify the config file:

  ```bash
  alembic -c alembic.ini upgrade head
  ```

### Configure environment variables

7. **Edit `.env` with your configuration values.**

   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/chat_platform
   READ_REPLICA_DATABASE_URL=postgresql+asyncpg://read-replica-host:5432/chat_platform
   DB_FAILOVER_URL=postgresql+asyncpg://failover-host:5432/chat_platform
   DB_REGION=us-east-1
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_CREDENTIALS_PATH=path/to/service-account.json
   JWT_SECRET_KEY=your-256-bit-secret-key
   AES_KEY=your-32-char-aes-key
   REDIS_URL=redis://localhost:6379/0
   ```

8. **Initialize database connectivity:**

   ```bash
   python -c "from app.database.connection import init_db; import asyncio; asyncio.run(init_db())"
   ```

### Running the Application

**Development mode:**

```bash
python app/main.py
```

**Production mode:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**With auto-reload:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Local network quick check

- From the backend machine:

```bash
curl http://127.0.0.1:8000/health
```

- From another LAN device, replace with your machine IP:

```bash
curl http://10.71.144.2:8000/health
```

## Database Schema

The application uses PostgreSQL with the following main tables:

- `users` - User accounts and profiles
- `friends` - Friend requests and relationships
- `followers` - Follow/follower relationships
- `blocks` - User blocking records
- `messages` - Direct messages between users
- `posts` - Social media posts
- `groups` - Group chat rooms
- `group_members` - Group membership records
- `group_messages` - Messages within groups
- `group_posts` - Posts within groups
- `chat_settings` - User chat preferences

All tables use UUID primary keys for consistency and scalability.

## Security Features

- **Authentication**: Firebase token verification for all protected endpoints
- **Authorization**: User ownership validation for sensitive operations
- **Encryption**: AES-256 encryption for sensitive data (phone numbers, messages)
- **Privacy**: Granular content visibility controls
- **Rate Limiting**: Configurable request rate limits (extensible)
- **Input Validation**: Pydantic schemas for all API inputs
- **CORS**: Configured cross-origin resource sharing

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.

## Health Check

```bash
GET /health
```

Returns `{"status": "ok"}` when the service is running.

## Deployment

### Docker (Recommended)

1. **Build image:**

   ```bash
   docker build -t chattingapp-backend .
   ```

2. **Run container:**
   ```bash
   docker run -p 8000:8000 chattingapp-backend
   ```

### Production Considerations

- Use environment-specific configuration files
- Set up proper logging and monitoring
- Configure database connection pooling
- Enable HTTPS/TLS
- Set up reverse proxy (nginx)
- Configure firewall rules
- Regular security updates
- Database backups and recovery

## Development

### Code Style

- Follow PEP 8 conventions
- Use type hints throughout
- Write comprehensive docstrings
- Maintain consistent naming

### Testing

Install test dependencies before running backend tests:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app
```

### Linting

```bash
# Check code quality
flake8 app/
black app/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper tests
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Check the API documentation at `/docs`
- Review the code comments and docstrings
- Create an issue in the repository
