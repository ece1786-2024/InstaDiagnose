from openai import OpenAI
import numpy as np
import json

class Doctor:
    def __init__(self, key, df_embed, threshold=0.75):
        self._client = OpenAI(api_key=key)
        self._threshold = threshold
        self._df_embed = df_embed

        # Create three GPT agents with different roles
        self._diagnosis_agent = {
            "role": "system",
            "content": """You are an experienced virtual family doctor with comprehensive medical knowledge. Collect symptom descriptions from the user and generate a list of possible illnesses.

    Instructions:
    1. Determine if the patient has more questions:
        - If the patient clearly states they have no more questions, set "if_continue" to 0.
        - Otherwise, set "if_continue" to 1.
    2. Gather detailed symptom descriptions from the conversation history.
    3. Generate a list of exactly 4 possible illnesses, ranked by relevance.
    4.PLEASE FOLLOW THE OUTPUT FORMAT:
        {
        "if_continue": 1,
        "illness_list": ["Illness1", "Illness2", "Illness3", "Illness4"]
        }
    """
        }

        self._inquiry_agent = {
    "role": "system",
    "content": """ You are an experienced virtual family doctor with comprehensive medical knowledge. Based on the conversation history and similarity score, ask the user more questions or summarize possible illnesses.

    Instructions:
    1. Review the conversation history and the similarity score.
    2. If the similarity score is above the threshold:
       - Summarize the possible illnesses.
       - Ask if the user wants to provide more information.
    3. If the similarity score is below the threshold:
       - Based on the collected information, ask more targeted and specific follow-up questions to clarify or expand on the symptoms.
       - Include questions about the user's medical history and any medications they are currently using, if the patient has not provided this information before.
    4. If the user has no further questions, summarize the possible illnesses. Remember to provide exactly 4 possible illnesses and no additional information after the user has no more questions.
    Maintain an empathetic and professional tone.
    Note: Do not mention the similarity score or threshold to the user.
    """
        }

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



    def _diagnose(self, prompt):
        messages = [
            self._diagnosis_agent,
            {"role": "user", "content": prompt}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages = messages
        )
        return response.choices[0].message.content


    def _diagnose_rag(self, prompt, context):
        messages = [
            self._diagnosis_agent,
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": f"These cases are provided as reference examples only. Please also use your medical knowledge and expertise to make a comprehensive diagnosis, considering both these cases and other relevant medical conditions that may apply:\n{context}"}
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


    def _check_format(self, agent, input, context=None):
        """
        The function ensures responses from different AI agents are in the correct format.

        agent: The specific agent to use (diagnose, diagnose with RAG, or comparison)
        input: prompt for the agent
        context: context message for diagnose with RAG agent

        return: agent responses
        """
        if agent == self._diagnose:
            response = self._diagnose(input)
            while True:
                try:
                    response = json.loads(response)
                    if_continue = response['if_continue']
                    diagnosis = response['illness_list']
                    return if_continue, diagnosis
                except:
                    # print(f'diagnose (wrong format): {response}')
                    response = self._diagnose(input)
                    continue

        elif agent == self._diagnose_rag:
            response = self._diagnose_rag(input, context)
            while True:
                try:
                    response = json.loads(response)
                    diagnosis = response['illness_list']
                    return diagnosis
                except:
                    # print(f'diagnose RAG (wrong format): {response}')
                    response = self._diagnose_rag(input, context)

        elif agent == self._compare_similarity:
            input1 = input[0]
            input2 = input[1]
            while True:
                response = self._compare_similarity(input1, input2)
                try:
                    similarity = float(response)
                    return similarity
                except:
                    # print(f'similarity (wrong format): {response}')
                    continue


    def _get_embedding(self, text, model="text-embedding-3-small"):
        text = text.replace("\n", "")
        return self._client.embeddings.create(input = [text], model=model).data[0].embedding


    def ask_doctor(self, threshold, diagnoses_list, full_history):
        """
        Function to interact with doctor model

        threshold: similarity score thershold
        diagnoses_list: historical list of previous diagnoses
        full_history: complete conversation history and diagnoses

        return: if_continue, diagnosis, response, full_history
        """ 
        # Extract patient-doctor conversation from full history
        doctor_patient_conversatin = []

        for i in range(0, len(full_history), 3):
            doctor_patient_conversatin.append(full_history[i])
            try:
                doctor_patient_conversatin.append(full_history[i+2])
            except:
                pass

        prompt = "Conversation History: " + "\n" + '\n'.join(doctor_patient_conversatin)

        # Uses GPT to generate a diagnosis and determine if the patient would like to terminate the conversation
        if_continue, diagnosis = self._check_format(self._diagnose, prompt)

        # Compares the new diagnosis with the previous one to calculate similarity
        similarity = 0
        if len(diagnoses_list) >= 1:
            similarity = self._check_format(self._compare_similarity, [diagnoses_list[-1], diagnosis])

        # If continue: generate follow-up questions considering the similarity score
        if if_continue == 1:
            full_history.append(f"Diagnosis: {diagnosis}")
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + f"\n\nSimilarity Score: {similarity}\nThreshold: {threshold}"

        # If end, use diagnose agent with RAG for final diagnosis
        else:
            # Get user input history
            input_history = '\n'.join([full_history[i] for i in range(0, len(full_history)-1, 3)])
            input_history = self._translation(input_history)
            input_embedding = self._get_embedding(input_history)

            # Calculate and sort cosine similarity
            self._df_embed['similarity'] = self._df_embed['embeddings'].apply(lambda x: np.dot(x, input_embedding))
            self._df_embed.sort_values('similarity', ascending=False, inplace=True)

            # Generate RAG prompt
            context = '\n'.join(self._df_embed.iloc[:4]['text'].values)
            
            # Improve prompt for diagnosis agent with external information
            diagnosis = self._check_format(self._diagnose_rag, prompt, context)
            full_history.append(f"Diagnosis: {diagnosis}")

            prompt = f"Conversation History: \n" + '\n'.join(full_history) + "\n\nThe patient has no further questions, please summarize the possible illnesses for the user and advise them to consult a medical professional."

        response = self._inquiry(prompt)
        full_history.append(f"Doctor: {response}")

        return if_continue, diagnosis, response, full_history


    def ask(self, if_return=False):
        """
        Interaction loop for diagnosis chatbot.
        """
        full_history = []
        diagnoses_list = []
        threshold = self._threshold
        if_continue = 1
        print("Doctor: Hello! I'm your virtual doctor. Please describe your symptoms or concerns.\n")

        while if_continue==1:
            user_input = input("Patient: ")
            full_history.append(f"Patient: {user_input}\n")

            if_continue, diagnosis, response, full_history = self.ask_doctor(threshold, diagnoses_list, full_history)
            diagnoses_list.append(diagnosis)

            print(f"\nDoctor: {response}", '\n')

        if if_return:
            return full_history, diagnoses_list