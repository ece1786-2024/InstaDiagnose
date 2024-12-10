import json
from openai import OpenAI
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


class Doctor:
    def __init__(self, key, df_embed, threshold=0.75):
        self._client = OpenAI(api_key=key)
        self._threshold = threshold

        # Use the global variables
        self._df_embed = df_embed

        # Create two GPT agents with different roles
        self._diagnosis_agent = {
            "role": "system",
    "content": """ You are an experienced virtual family doctor with comprehensive medical knowledge.  Collect symptom descriptions from the user and generate a list of possible illnesses.

    Instructions:
    1. Determine if the patient has more questions:
    - If the patient clearly states they have no more questions, set "if_continue" to 0.
    - Otherwise, set "if_continue" to 1.
    2. Gather detailed symptom descriptions from the conversation history.
    3. Review the conversation history to determine if the patient has already provided information about medical history, current medications, or additional symptoms:
       - If the patient has not provided this information, ask them about it.
       - If the patient has already provided this information, avoid repeating the question. Instead, based on the collected information, ask more targeted and specific follow-up questions to clarify or expand on the symptoms.
    4. Generate a list of exactly 4 possible illnesses, ranked by relevance.
    5. Generate a response:
    - If the similarity score is above a threshold, summarize the possible illnesses for the user and ask if the user would like to provide more information about their symptoms.
    - If the similarity score is below a threshold, ask the user for more information about their symptoms.
    - If the user has no further questions, summarize the possible illnesses for the user and advise them to consult a medical professional.
    
    
**YOU MUST FOLLOW THE OUTPUT FORMAT**:
{
    "if_continue": 1,
    "illness_list": ["Illness1", "Illness2", "Illness3", "Illness4"],
    "response":""
}
    """}

        self._similarity_agent = {

            "role": "system",
            "content": """You are an assistant responsible for calculating the similarity score between two lists of illnesses.

          Instructions:
          1. Receive two lists of illnesses.
          2. Standardize illness names (e.g., "heart attack" and "myocardial infarction" are considered the same).
          3. Calculate the similarity score as follows:
            - Compare the current list of illnesses to the previous list.
            - If three illnesses in the current list are the same as in the previous list, assign a score of 3/4 (0.75).
            - If two illnesses are the same, assign a score of 2/4 (0.5).
            - If one illness is the same, assign a score of 1/4 (0.25).
            - If no illnesses match, assign a score of 0.
          4. Return the similarity score as a float only and DO NOT EXPLAIN.

          Output Format:
          Float number: One of the following values: 0.75, 0.5, 0.25, or 0.
          """
        }

        self._translation_agent = {
            "role": "system",
            "content": """Read the conversation history and summarize the patient's descriptions as symptoms. Return the symptoms as a list."""
        }


    def _translation(self, prompt):
        messages = [
            self._translation_agent,
            {"role": "user", "content": prompt}
        ]
        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages = messages
        )
        return response.choices[0].message.content
    

    def _get_embedding(self, text, model="text-embedding-3-small"):
        response = self._client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding


    def _get_relevant_conditions(self, full_history, top_k=4):
        # Combine all patient inputs into one query
        combined_query = '\n'.join([full_history[i] for i in range(0, len(full_history)-1, 3)])
        combined_query = self._translation(combined_query)

        # Get embedding for the query
        query_embedding = self._get_embedding(combined_query)

        # Calculate similarities
        similarities = self._df_embed['embeddings'].apply(lambda x: np.dot(x, query_embedding))

        # Get top k most similar cases
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        context = """Reference Cases from Medical Database:
    (Note: These cases are provided as reference examples only. Please also use your medical knowledge and expertise to make a comprehensive diagnosis, considering both these cases and other relevant medical conditions that may apply)

    """
        for idx in top_indices:
            context += f"Case: {self._df_embed['text'].iloc[idx]}\n"

        return context

    def _doctor(self, prompt):
        messages = [
            self._diagnosis_agent,
            {"role": "user", "content": prompt} #enhanced_prompt}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        return response.choices[0].message.content
    

    def _doctor_rag(self, prompt, context):
        messages = [
            self._diagnosis_agent,
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": context}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages = messages
        )
        return response.choices[0].message.content


    def _compare_similarity(self, input1, input2):
        messages = [
            self._similarity_agent,
            {"role": "user", "content": f"Compare the similarity between these two inputs:\n1: {input1}\n2: {input2}"}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        return response.choices[0].message.content

    def _check_format(self, agent, input, context=None):
        if agent == self._doctor:
            response = self._doctor(input)
            while True:
                try:
                    response = json.loads(response)
                    if_continue = response['if_continue']
                    diagnosis = response['illness_list']
                    question = response['response']
                    return if_continue, diagnosis, question
                except:
                    response = self._doctor(input)
                    continue
        
        elif agent == self._doctor_rag:
            response = self._doctor_rag(input, context)
            while True:
                try:
                    response = json.loads(response)
                    if_continue = response['if_continue']
                    diagnosis = response['illness_list']
                    question = response['response']
                    return if_continue, diagnosis, question
                except:
                    response = self._doctor_rag(input, context)


        elif agent == self._compare_similarity:
            input1 = input[0]
            input2 = input[1]
            response = self._compare_similarity(input1, input2)
            while True:
                try:
                    similarity = float(response)
                    return similarity
                except:
                    response = self._compare_similarity(input1, input2)
                    continue

    def ask_doctor(self, threshold, diagnoses_list, full_history):
        similarity = 0
        if len(diagnoses_list) >= 2:
            similarity = self._check_format(self._compare_similarity, [diagnoses_list[-1], diagnoses_list[-2]])

        if_continue, _, _ = self._check_format(self._doctor, full_history[-1])

        if if_continue == 1:
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + f"\n\nSimilarity Score: {similarity}\nThreshold: {threshold}"
            if_continue, diagnosis, question = self._check_format(self._doctor, prompt)
        else:
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + "\n\nThe patient has no further questions, please provide your final diagnosis."
            context = self._get_relevant_conditions(full_history)
            if_continue, diagnosis, question = self._check_format(self._doctor_rag, prompt, context)
        
        full_history.append(f"Diagnosis: {diagnosis}")
        full_history.append(f"Doctor: {question}")
        return if_continue, diagnosis, question, full_history

    def ask(self, if_return=False):
        full_history = []
        diagnoses_list = []

        threshold = self._threshold
        if_continue, similarity = 1, 0.0
        print("Doctor: Hello! I'm your virtual doctor. Please describe your symptoms or concerns.\n")

        while if_continue==1:
            user_input = input("Patient: ")

            full_history.append(f"Patient: {user_input}")

            if_continue, diagnosis, question, full_history = self.ask_doctor(threshold, diagnoses_list, full_history)
            diagnoses_list.append(diagnosis)

            print(f"\nDoctor: {question}\n")

        if if_return:
            return similarity, full_history, diagnoses_list
