from openai import OpenAI
import numpy as np
import json

class Doctor:
    def __init__(self, key, threshold=0.75):
        self._client = OpenAI(api_key=key)
        self._threshold = threshold

        self._doctor_agent = {
    "role": "system",
    "content": """You are a virtual family doctor. Collect symptom descriptions from the user and generate a list of possible illnesses.

Instructions:
1. Determine if the patient has more questions:
   - If the patient clearly states they have no more questions, set "if_continue" to 0.
   - Otherwise, set "if_continue" to 1.
2. Gather detailed symptom descriptions from the conversation history.
3. Ask the user if they have any other medical history or are currently using any medications or additional symptoms.
4. Generate a list of exactly 4 possible illnesses, ranked by relevance.
5. Generate a response:
   - If the user has no further questions, summarize the possible illnesses for the user and advise them to consult a medical professional.
   - Otherwise, ask the user for more information about their symptoms to improve the accuracy of the diagnosis.

Output Format:
{
  "if_continue": 1,
  "illness_list": ["Illness1", "Illness2", "Illness3", "Illness4"],
  "response":""
}
"""
        }

    # Function to interact with the doctor agent
    def _doctor(self, prompt):
        messages = [
            self._doctor_agent,
            {"role": "user", "content": prompt}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        return response.choices[0].message.content


    def _check_format(self, agent, input):
        """
        The function ensures responses from different AI agents are in the correct format.

        agent: The specific agent to use (doctor, doctor with RAG, or comparison)
        input: prompt for the agent

        return: agent responses
        """
        if agent == self._doctor:
            while True:
                response = self._doctor(input)
                try:
                    response = json.loads(response)
                    if_continue = response['if_continue']
                    diagnosis = response['illness_list']
                    question = response['response']
                    _ = diagnosis[0]
                    return if_continue, diagnosis, question
                except:
                    continue


    def ask_doctor(self, _t=None, _d=None, full_history=None):
        """
        Function to interact with doctor model

        full_history: complete conversation history and diagnoses

        return: if_continue, diagnosis, question, full_history
        """ 
        if_continue, _, _ = self._check_format(self._doctor, full_history[-1])
        if if_continue == 1:
            prompt = f"Conversation History: \n" + '\n'.join(full_history)
        else:
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + "\n\nThe patient has no further questions, please summarize the possible illnesses for the user and advise them to consult a medical professional."

        if_continue, diagnosis, question = self._check_format(self._doctor, prompt)
        full_history.append(f"Doctor: {question}")

        return if_continue, diagnosis, question, full_history
    
    def ask(self, if_return=False):
        full_history = []
        diagnoses_list = []

        threshold = self._threshold
        if_continue= 1
        response = "Doctor: Hello! I'm your virtual doctor. Please describe your symptoms or concerns.\n"
        print(response)

        while if_continue==1:
            user_input = input("Patient: ")
            full_history.append(f"Patient: {user_input}")
            if_continue, diagnosis, response, full_history = self.ask_doctor(None, None, full_history)

            diagnoses_list.append(diagnosis)

            print(f"\nDoctor: {response}\n")
        
        if if_return:
            return full_history, diagnoses_list
        
