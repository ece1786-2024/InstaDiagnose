from openai import OpenAI
import json

class Doctor:
    def __init__(self, key, threshold=0.85):
        self._client = OpenAI(api_key=key)
        self._threshold = threshold

        # Create two GPT agents with different roles
        self._doctor_agent = {
                    "role": "system",
                    "content": """You are a virtual family doctor. Collect symptom descriptions from the user and generate a list of possible illnesses.

        Instructions:
        1. Gather detailed symptom descriptions from the conversation history.
        2. Generate a list of exactly 4 possible illnesses, ranked by relevance.
        3. Determine if the patient has more questions:
        - If the patient clearly states they have no more questions, set "if_continue" to 0.
        - Otherwise, set "if_continue" to 1.
        4. Generate a response:
        - If the similarity score is above a threshold, summarize the possible illnesses for the user and ask if the user would like to provide more information about their symptoms.
        - If the similarity score is below a threshold, ask the user for more information about their symptoms to improve the accuracy of the diagnosis.
        - If the user has no further questions, summarize the possible illnesses for the user and advise them to consult a medical professional.

        Output Format:
        {
        "if_continue": 1,
        "illness_list": ["Illness1", "Illness2", "Illness3", "Illness4"],
        "response":""
        }
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

        RETURN OUTPUT IN THIS FORMAT:
            Float number between 0 and 1.
        """
        }

    # Function to interact with doctor agent
    def _doctor(self, prompt):
        messages = [
            self._doctor_agent,
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
        if agent == self._doctor:
            while True:
                response = self._doctor(input)
                try:
                    response = json.loads(response)
                    if_continue = response['if_continue']
                    diagnosis = response['illness_list']
                    question = response['response']
                    return if_continue, diagnosis, question
                except:
                    continue

        elif agent == self._compare_similarity:
            input1 = input[0]
            input2 = input[1]
            while True:
                response = self._compare_similarity(input1, input2)
                try:
                    similarity = float(response)
                    return similarity
                except:
                    continue
    
    def ask_doctor(self, threshold, diagnoses_list, full_history, if_continue, similarity):
        if if_continue == 1:
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + f"\n\nSimilarity Score: {similarity}\nThreshold: {threshold}"
        else:
            prompt = f"Conversation History: \n" + '\n'.join(full_history) + "\n\nThe patient has no further questions, please summarize the possible illnesses for the user and advise them to consult a medical professional."
            if_continue, diagnosis, question = self._check_format(self._doctor, prompt)
            full_history.append(f"Doctor: {question}")
            return if_continue, diagnosis, question, full_history, similarity

        if_continue, diagnosis, question = self._check_format(self._doctor, prompt)

        if len(diagnoses_list) >= 1:
            similarity = self._check_format(self._compare_similarity, [diagnoses_list[-1], diagnosis])

        full_history.append(f"Doctor: {question}")

        return if_continue, diagnosis, question, full_history, similarity

    def ask(self, if_return=False):
        full_history = []
        diagnoses_list = []

        threshold = self._threshold
        if_continue, similarity = 1, 0.0
        response = "Enter your medical question: "

        while if_continue==1:
            print(response)
            user_input = input()
            full_history.append(f"Patient: {user_input}")
            if_continue, diagnosis, response, full_history, similarity = self.ask_doctor(threshold, diagnoses_list, full_history, if_continue, similarity)

            diagnoses_list.append(diagnosis)
        print(response)
        
        if if_return:
            return similarity,full_history, diagnoses_list
        
        return similarity