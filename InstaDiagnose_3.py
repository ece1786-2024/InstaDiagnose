from openai import OpenAI
import numpy as np
import json

class Doctor:
    def __init__(self, key, threshold=0.85):
        self._client = OpenAI(api_key=key)
        self._threshold = threshold

        # Create three GPT agents with different roles
        self._diagnosis_agent = {
            "role": "system",
            "content": """You are a virtual family doctor. Collect symptom descriptions from the user and generate a list of possible illnesses.

Instructions:
1. Gather detailed symptom descriptions from the conversation history.
2. Generate a list of exactly 4 possible illnesses, ranked by relevance.
3. Determine if the patient has more questions:
   - If the patient clearly states they have no more questions, set "if_continue" to 0.
   - Otherwise, set "if_continue" to 1.
4.

Output Format:
{
  "if_continue": 1,
  "illness_list": ["Illness1", "Illness2", "Illness3", "Illness4"]
}
"""
        }

        self._inquiry_agent = {
            "role": "system",
            "content": """You are a virtual family doctor. Based on the conversation history and similarity score, ask the user more questions or summarize possible illnesses.

Instructions:
1. Review the conversation history and the similarity score.
2. If the similarity score is above the threshold:
   - Summarize the possible illnesses.
   - Ask if the user wants to provide more information.
3. If the similarity score is below the threshold:
   - Ask specific questions to gather more symptom details.
4. If the user has no further questions, summarize the possible illnesses. Remember that just give 4 possible illness and no need to give other information after the user has no more question.

Maintain an empathetic and professional tone.

Note: Do not mention the similarity score or threshold to the user.
"""
        }

        self._similarity_agent = {
            "role": "system",
            "content": """You are an assistant responsible for calculating the similarity between two illness lists.

Instructions:
1. Receive two lists of illnesses.
2. Standardize illness names (e.g., "heart attack" and "myocardial infarction" are the same).
3. Calculate the similarity as a float between 0 and 1.
   - Use the number of common illnesses divided by the total unique illnesses.
4. Return the similarity as a float only and DO NOT EXPLAIN.

Output Format:
Float number between 0 and 1.
"""
        }


    # Function to interact with doctor agent
    def _diagnose(self,prompt):
        messages = [
            self._diagnosis_agent,
            {"role": "user", "content": prompt}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages = messages
        )
        return response.choices[0].message.content


    def _inquiry(self, prompt):
        messages = [
            self._inquiry_agent,
            {"role": "user", "content": prompt}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages = messages
        )
        return response.choices[0].message.content


    # Function to compare similarities between previous and new diagnoses using the similarity agent
    def _compare_similarity(self, input1, input2):
        messages = [
            self._similarity_agent,
            {"role": "user", "content": f"Compare the similarity between these two inputs:\n1: {input1}\n2: {input2}"}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages = messages
        )
        return response.choices[0].message.content
    

    def _check_format(self, agent, input):
        if agent == self._diagnose:
            while True:
                response = self._diagnose(input)
                try:
                    response = json.loads(response)
                    if_continue = response['if_continue']
                    diagnosis = response['illness_list']
                    return if_continue, diagnosis
                except:
                    continue

        elif agent == self._compare_similarity:
            input1 = input[0]
            input2 = input[1]
            while True:
                response = self._compare_similarity(input1, input2)
                # print(f"Compare Similarity Response: {response}")
                try:
                    similarity = float(response)
                    return similarity
                except:
                    continue


    def ask_doctor(self, threshold, diagnoses_list, full_history):
        prompt = "Conversation History: " + "\n" + "\n".join(full_history)
        if_continue, diagnosis = self._check_format(self._diagnose, prompt)
        full_history.append(f"Diagnosis: {diagnosis}")

        similarity = 0
        if len(diagnoses_list) >= 1:
            similarity = self._check_format(self._compare_similarity, [diagnoses_list[-1], diagnosis])

        if if_continue == 1:
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + f"\n\nSimilarity Score: {similarity}\nThreshold: {threshold}"
        else:
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + "\n\nThe patient has no further questions, please summarize the possible illnesses for the user and advise them to consult a medical professional."
            response = self._inquiry(prompt)
            full_history.append(f"Doctor: {response}")
            return if_continue, diagnosis, response, full_history

        response = self._inquiry(prompt)
        full_history.append(f"Doctor: {response}")

        return if_continue, diagnosis, response, full_history
    

    def ask(self, if_return=False):
        full_history = []
        diagnoses_list = []
        threshold = self._threshold
        if_continue = 1
        response = "Enter your medical question: "

        while if_continue==1:
            print(response)
            user_input = input()
            full_history.append(f"Patient: {user_input}")
            if_continue, diagnosis, response, full_history = self.ask_doctor(threshold, diagnoses_list, full_history)

            diagnoses_list.append(diagnosis)

        print(response)

        if if_return:
            return full_history, diagnoses_list