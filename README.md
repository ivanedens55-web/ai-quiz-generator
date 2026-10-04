# AI Quiz Generator

A small web app that turns any topic into a multiple-choice quiz using Google Gemini. Type a topic, pick how many questions and how hard, answer them, and get your score with an explanation for every question.

Built with Python and Streamlit as a beginner-friendly example of calling an LLM, requesting structured JSON, and validating the response before using it.

## Features

- Generate a quiz on any topic you type in
- Choose 3 to 10 questions
- Choose a difficulty: Easy, Medium, or Hard
- Every question has 4 options, one correct answer, and a short explanation
- Answer in the browser and submit when you're done (all questions must be answered)
- See your score, which questions you got right or wrong, the correct answers, and explanations
- Start a new quiz at any time
- Safe handling of AI output: invalid JSON, missing fields, wrong option counts, duplicate options, and answers that don't match an option are caught, and invalid questions are skipped rather than crashing the app
- Clear error messages for a missing or invalid API key, rate limits, unavailable models, and network problems

## Tech stack

| Tool | Purpose |
| --- | --- |
| Python 3.10+ | Language |
| [Streamlit](https://streamlit.io/) | Web interface |
| [Google Gemini API](https://ai.google.dev/) via the `google-genai` SDK | Generates the questions |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Loads the API key from a `.env` file |

No database, authentication, or Docker.

## How it works

1. **You choose the settings.** `app.py` collects the topic, number of questions, and difficulty.
2. **Gemini writes the quiz.** `ai.py` sends a prompt asking for JSON in this shape, with Gemini's JSON response mode turned on:

   ```json
   {
     "questions": [
       {
         "question": "...",
         "options": ["...", "...", "...", "..."],
         "correct_answer": "...",
         "explanation": "..."
       }
     ]
   }
   ```

3. **The response is validated.** `ai.py` parses the JSON (stripping Markdown code fences or stray text if present) and checks each question: it must have question text, exactly 4 distinct non-empty options, and a correct answer that matches one of the options. Small mismatches are fixed, such as different capitalisation or the model answering with a letter like `"B"`. Questions that still fail are dropped. If none are valid, you see an error and can try again.
4. **You take the quiz.** Answers are compared with the validated correct answer to calculate your score.

## Project structure

```
ai-quiz-generator/
├── app.py            # Streamlit interface: settings, quiz, scoring, results
├── ai.py             # Gemini call, prompt, JSON parsing and validation
├── requirements.txt  # Python dependencies
├── .env.example      # Template for your API key
├── .gitignore        # Keeps .env and other local files out of Git
└── README.md
```

## Getting a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and sign in with a Google account.
2. Click **Create API key** and copy it.
3. Keep it private. Never commit it to GitHub.

The free tier is enough to try this project, but usage limits apply and can change; check Google's current [pricing and rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Installation

Clone the repository and move into it:

```bash
git clone https://github.com/<your-username>/ai-quiz-generator.git
cd ai-quiz-generator
```

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Copy the example environment file:

```bash
# macOS / Linux
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Open `.env` and paste your key:

```
GEMINI_API_KEY=your_actual_key_here
```

The app uses `gemini-3.5-flash` by default. To use a different model, add a line such as `GEMINI_MODEL=gemini-2.5-flash` to `.env`. Available models are listed in the [Gemini models documentation](https://ai.google.dev/gemini-api/docs/models).

`.env` is listed in `.gitignore`, so your key stays on your machine.

## Running locally

```bash
streamlit run app.py
```

Streamlit opens the app in your browser, usually at http://localhost:8501.

## Example usage

1. Enter **Java OOP** as the topic.
2. Set **Number of questions** to 5 and **Difficulty** to Medium.
3. Click **Generate Quiz**.
4. Pick an answer for each question, for example:

   > **1. Which OOP principle restricts direct access to an object's fields?**
   > - Inheritance
   > - Encapsulation
   > - Polymorphism
   > - Abstraction

5. Click **Submit Quiz** to see your score (for example `4 / 5`), with the questions you missed expanded to show the correct answer and explanation.
6. Click **Start a new quiz** to try another topic.

Questions are generated fresh every time, so the same topic gives a different quiz on each run.

## Troubleshooting

| Message | Fix |
| --- | --- |
| `GEMINI_API_KEY is not set` | Create `.env` from `.env.example` and add your key. Restart the app. |
| `Gemini rejected the API key` | Check the key was copied fully, with no quotes or spaces. |
| `The model ... was not found` | Set `GEMINI_MODEL` in `.env` to a model from Google's current list. |
| `rate limit or quota reached` | Wait a minute and try again, or check your quota in Google AI Studio. |

## Future improvements

- Shuffle answer options so the correct answer position varies
- Timer mode for each quiz
- Export results or the quiz to PDF or CSV
- Topic suggestions and quiz history within a session
- Unit tests and a GitHub Actions workflow to run them
- Deploy to Streamlit Community Cloud

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.