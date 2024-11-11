# API Automation Agent

An open-source AI Agent that automatically generates an automation framework from your OpenAPI/Swagger specification, based on the api-framework-ts-mocha template (https://github.com/damianpereira86/api-framework-ts-mocha).

## Features

- Generates type-safe service and data models
- Generates test suites for every endpoint
- Uses AI to review and fix code issues and ensure code quality and best practices
- Includes code formatting and linting
- Runs tests with detailed reporting and assertions

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- OpenAI API key or Anthropic API key

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/api-automation-agent.git
    cd api-automation-agent
    ```

2. Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Set up environment variables:
    ```bash
    cp example.env .env
    ```

4. Edit the `.env` file with your API keys:
    ```
    OPENAI_API_KEY=your_openai_api_key_here
    ANTHROPIC_API_KEY=your_anthropic_api_key_here
    ```

## Usage

Run the agent using the following command:

```bash
python src/main.py path/to/your/openapi.yaml
```

### Options

- `--destination-folder`: Specify output directory (default: ./generated-framework_[timestamp])
- `--endpoint`: Generate framework for a specific endpoint only

### Example

```bash
python src/main.py api-spec.yaml --destination-folder ./my-api-client
```

After running, you'll be prompted to choose:
1. Generate Models only
2. Generate Models and Tests

The generated framework will be created in your specified destination folder.

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Reporting Issues

Found a bug or have a suggestion? Please open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment details (OS, Python version, etc.)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI and Anthropic for their AI models
- The Endava Testing Discipline in Uruguay for inspiration and support