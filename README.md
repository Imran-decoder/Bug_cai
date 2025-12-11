# 🐞 Bug CAI – README



This document explains the purpose, flow, and functionality , the main execution file of the **Bug CAI** project.

---

## 📌 **Overview**

`main.py` is the central script that powers the Bug CAI application.
It provides a **command-line interface (CLI)** where users can:

* Upload a **Python file**
* Automatically scan the file for **bugs**, **errors**, and **bad practices**
* Receive fixes, explanations, and improved code generated using an **LLM (Gemini API)**

The script acts as a bridge between:

1. **User input**
2. **Code processing logic**
3. **Gemini AI error-handling engine**

---

## 🔧 **How `main.py` Works**

### **1️⃣ File Input**

The script prompts you to enter the path of the Python file you want to analyze:

```python
file_path = input("Enter your file path: ")
```

It then checks if the file exists and reads the source code.

---

### **2️⃣ Code Preprocessing**

Before sending code to the LLM, it:

* Reads the file content
* Removes dangerous characters or unnecessary whitespace
* Prepares the code string for analysis

---

### **3️⃣ LLM Request (Gemini API)**

`main.py` sends the code to the Gemini model for bug detection and improvement.

The prompt typically includes:

* Full code
* Request for debugging
* Request for optimized corrected code

Example prompt structure:

```python
prompt = f"""
Analyze the following Python code for errors and fix them.
Provide:
1. A list of bugs found
2. Corrected code
3. Explanation of the fixes
Code:
{code}
"""
```

---

### **4️⃣ AI Response Parsing**

The response is returned as a structured message.
The script extracts:

* **Bug list**
* **Improved code**
* **Explanations**

and displays them to the user.

---

### **5️⃣ Output to User**

The final output includes:

* Clear bug descriptions
* Corrected and optimized code
* Reason behind each fix

This makes the tool helpful for:

✔ Debugging
✔ Learning Python
✔ Improving coding skills

---

## 📦 **Key Features of `main.py`**

| Feature               | Description                              |
| --------------------- | ---------------------------------------- |
| AI-based debugging    | Uses Google Gemini to detect code issues |
| Automatic code fixing | Returns fully corrected Python code      |
| Error explanations    | Helps users understand mistakes          |
| CLI interface         | Simple, interactive usage                |
| Safe file handling    | Validates input file path                |

---

## ▶️ **How to Run `main.py`**

```bash
python main.py
```

Then enter the path of the Python file you want to analyze.

Example:

```
Enter your file path: ./examples/test.py
```

---
LangChain Components ---
LangChain Component	Purpose
ChatGoogleGenerativeAI	Gemini model wrapper
PromptTemplate	Creates a dynamic prompt for debugging
LLMChain	Pipeline that sends prompt + input → gets output
Structured Output (optional)	Formats AI response in JSON-like way

## 📁 **File Responsibility**

`main.py` handles:

* CLI + user interaction
* Reading Python files
* Sending prompt to AI
* Displaying results

It does **not** handle:

* Logging
* GUI
* Multi-file projects
* Training models

---


