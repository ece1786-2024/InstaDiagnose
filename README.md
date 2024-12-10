# InstaDiagnose

Access to timely and high-quality healthcare is a growing challenge in Canada, with patients often facing long wait times to receive the care they need. In 2023, the median wait time from a general practitioner referral to treatment was 27.7 weeks—the longest ever recorded [1]. Such delays can worsen illnesses and complicate treatment [2].

To help address these issues, our project aims to create a virtual “family doctor” tool for primary care. This system will allow users to input their symptoms and receive immediate and reliable suggestions of potential diseases they may have. This tool can empower individuals to seek appropriate care earlier and more efficiently.

Machine learning supports this solution because it can effectively handle the complexity and variability of human health descriptions. Consequently, this approach ensures that each user’s unique input, no matter how nuanced or informal, is translated into meaningful, tailored health insights.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/ece1786-2024/InstaDiagnose.git
    ```

2. Install packages:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Run in Terminal
a. Set an API key:

  ```bash
  api_key = 'ENTER YOUR API KEY'
  ```

b. For RAG models, construct a dataframe for embedding:

  ```bash
  emb = pd.read_pickle('RAG_dataset/text_embeddings2.pkl')
  df_embed = pd.read_csv('RAG_dataset/text_embeddings2.csv')
  df_embed['embeddings'] = emb
  ```

c. Import a model:
   - **Class**: `Doctor`
   - **Parameters**:
     - **InstaDiagnose_1**, **InstaDiagnose_2**, and **InstaDiagnose_3**:
       - `key`: str, GPT API key.
       - `threshold`: float, threshold for similarity score (default = 0.75).
     - **RAG_Diagnose_2** and **RAG_Diagnose_3**:
       - `key`: str, GPT API key.
       - `df_embed`: DataFrame, embedding.
       - `threshold`: float, threshold for similarity score (default = 0.75).
   - **ask()**: Starts a conversation with the virtual doctor.
     - **Parameters**:
       - `if_return`: bool, default = False.  
     - **Returns**:
       - If `if_return`=True, returns the similarity score, full history of patient-doctor conversations and diagnoses, and a diagnoses list.
         
   (See code example in `model_sample_output.txt`.)

### 2. User Interface in `ask_doctor.ipynb`

a. Run the **Initialization** section.  
b. Navigate to the **Chatbot Interface** section.  
c. Run the first and second cells.
