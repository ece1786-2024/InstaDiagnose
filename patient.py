from openai import OpenAI

class Patient:
    def __init__(self, key):
        self._client = OpenAI(api_key=key)
    
    def reply(self, symptoms, disease, prompt):
        messages = [
        {   "role": "system",
            "content": f"""You are acting as a patient who is likely to have {disease} and the following symptoms: {symptoms}. You are now talkig to a doctor, and you do not have any medical knowledge. 
            Please descript your symptoms in detail and answer the doctor's question according to the disease and symptoms. 

            Respond to follow-up questions based on the symptoms listed for your condition in the dataset. Do not add unrelated symptoms or make up new information.

            **Answer the question in short. And simply say "I do not know" if you do not have enough information or knowledge to answer.**

            **Please ONLY say "I do not have more information." if you do not have enough information to answer.**"""},
        {    "role": "user", 
            "content": f"You are a patient, please answer the doctor's question based on your symptoms: {prompt}"
        }
        ]

        response = self._client.chat.completions.create(
        model="gpt-4o",
        messages=messages
        )

        return response.choices[0].message.content 