# Torre.ai AI-Powered Screening Process

A Proof of Concept (POC) for an AI-powered screening process simulation that enables candidates to complete initial screening interviews with Emma, Torre.ai's AI agent, through video/audio calls. Built following Hexagonal Architecture (Ports and Adapters) and Domain-Driven Design (DDD) principles.

## 🏗️ Project Structure

The project is organized into the following key directories:

### 📂 `app`

Contains the core of your framework.

### 📂 `src`

Contains the core of your application and the domain logic.

#### 📂 `bounded_contexts`

Contains the bounded contexts of your application.

#### 📂 `modules`

Contains the modules of your application.


### 📂 `tests`

Contains the tests of your application.

## 🎯 Purpose

This POC demonstrates an AI-powered screening system that:

- **For Candidates**: Provides flexible scheduling, consistent experience, and immediate engagement after application
- **For Recruiters/Job Posters**: Reduces manual screening time, standardizes evaluations, and provides data-driven insights
- **For Emma AI**: Enables scalable screening capacity with 24/7 availability

### Key Features

- Collects candidate applications via Torre.ai username and job offer URL
- Leverages Torre.ai APIs to gather candidate genome data and job requirements
- Conducts AI-powered screening calls with Emma asking tailored questions
- Analyzes call data to generate summaries and screening scores for job posters
- Follows event-driven architecture with `JobOfferApplied` and `UserLeftCall` events

### Architecture Benefits

- Clear separation of concerns (Domain, Application, Infrastructure layers)
- Domain-centric design with bounded contexts
- Framework independence (business logic decoupled from infrastructure)
- Highly testable code (each layer can be tested independently)
- Maintainable and scalable structure

## 🏛️ Architectural Overview

The project follows these key principles:

1. **Domain Layer** (`domain/`)
   - Contains the business logic
   - Pure Python with no external dependencies
   - Defines interfaces (ports) for external operations

2. **Application Layer** (`application/`)
   - Orchestrates the flow of data and implements use cases
   - Coordinates between the domain and infrastructure layers

3. **Infrastructure Layer** (`infrastructure/`)
   - Implements adapters for external services
   - Contains framework-specific code
   - Implements the interfaces defined in the domain layer

## 🚀 Getting Started

1. Clone this repository:
```bash
git clone <repository-url>
cd torreai-new-screening-process-approach
```

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or on Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Install dependencies using uv:
```bash
uv sync
```

This will:
- Create a virtual environment automatically
- Install all project dependencies from `pyproject.toml`
- Install development dependencies (pytest, pytest-cov)

4. Activate the virtual environment:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
# Or use uv run <command> to run commands in the virtual environment automatically
```

**Note**: This project uses `uv` for fast Python package management. See `pyproject.toml` for dependencies.

## 📝 Usage

### Development Workflow

1. **Create bounded contexts** under `src/bounded_context/`
2. **Define domain model** in the `domain/` layer (entities, value objects, ports)
3. **Implement use cases** in the `application/` layer (services, commands, queries)
4. **Add adapters** in the `infrastructure/` layer (API clients, repositories, external services)
5. **Write tests** following the same structure in `tests/`

### Key Components

- **Event-Driven Architecture**: System uses events (`JobOfferApplied`, `UserLeftCall`) to orchestrate workflows
- **Torre.ai Integration**: Fetches candidate profiles and job details via Torre.ai APIs
- **Emma AI Integration**: Conducts screening interviews with personalized questions
- **Real-time Transcription**: Captures conversation data during calls
- **Post-Call Analysis**: Generates summaries and fit assessments using embeddings and AI processing

## 🧪 Testing

Run tests using:
```bash
# Using uv (recommended)
uv run pytest

# Or activate venv and run directly
source .venv/bin/activate
pytest
```

## 📦 Project Dependencies

Current dependencies (Phase 1 Foundation):

- **httpx**: HTTP client for Torre.ai API integration
- **psycopg**: PostgreSQL adapter
- **pika**: RabbitMQ event publisher
- **pytest**: Testing framework (dev dependency)

All dependencies are managed via `uv` and defined in `pyproject.toml`. To add new dependencies:

```bash
uv add <package-name>        # Add runtime dependency
uv add --dev <package-name>  # Add development dependency
```

Future dependencies (to be added in later phases):

- **Event-Driven Framework**: For handling `JobOfferApplied` and `UserLeftCall` events
- **AI/LLM Service**: Emma AI integration for screening conversations
- **Transcription Service**: Real-time transcription of video/audio calls
- **Video/Audio Infrastructure**: Video/audio call functionality
- **Embeddings/Analysis Service**: Post-call analysis using embeddings and AI processing

See [AGENTS.md](./AGENTS.md) for more details on architecture and dependencies.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📚 Documentation

- **[AGENTS.md](./AGENTS.md)**: Comprehensive project context, agent ecosystem, and architectural patterns
- **[PRD](./docs/prds/PRD-torre-ai-screening-process.md)**: Product Requirements Document (v1.1)
- **[Folder Structure Rule](./.cursor/rules/folder-structure.mdc)**: Detailed folder organization guidelines

## 🏗️ Architecture

This project follows **Hexagonal Architecture** (Ports and Adapters) with **Domain-Driven Design**:

- **Domain Layer**: Pure business logic with no external dependencies
- **Application Layer**: Orchestrates use cases and coordinates between layers
- **Infrastructure Layer**: Implements adapters for external services

See [AGENTS.md](./AGENTS.md) for detailed architectural documentation.

## 📚 Additional Resources

- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Domain-Driven Design (Eric Evans)](https://domainlanguage.com/ddd/)
- [Torre.ai API Documentation](https://torre.ai)

## ⚠️ Project Status

**This is a Proof of Concept (POC)** - formal SLAs and detailed metrics are not required. The project is in active development, and many technical decisions (framework, dependencies, deployment) are still to be determined during implementation.