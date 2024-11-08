# API Automation Agent

## Setup

Before you begin, make sure you have Node.js and Python installed on your machine.

1. Install dependencies 
    ```bash
    pip install -r requirements.txt
    ```

2. Copy the `example.env` file provided in the project directory:

    ```bash
    cp example.env .env
    ```

3. Open the `.env` file and update the following properties with your local environment values:

    ```yaml
    OPENAI_API_KEY=
    ```

After that, you should be able to run it through the src/main.py file.

## Results

After the agent starts, a folder starting with "generated-framework_" will be created with the results.