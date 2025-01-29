from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI 
from langchain.llms import OpenAI
from langchain.chains import LLMChain, SequentialChain
import os
import getpass
import click
import time
from bkbit.knowledge_extraction.pdf_extraction import load_pdf, split_documents

def create_assertion_extraction_chain(llm):
    """
    Creates an assertion extraction chain for extracting factual or declarative assertions from neuroscience text.

    Args:
        llm: The language model used for generating prompts.

    Returns:
        LLMChain: The assertion extraction chain.

    Raises:
        None.
    """
    # Prompt for extracting assertion statements
    assertion_prompt = PromptTemplate(
        input_variables=["text_chunk"],
        template="""
    You are an AI assistant trained to carefully read neuroscience text and extract all statements that present factual or declarative assertions.
    The definition of a statement is: "A statement made by a particular agent on a particular occasion that a particular proposition is true, based on the evaluation of one or more lines of evidence.
    The identity of a particular assertion is dependent upon (1) what it claims to be true (its semantic content, aka its ‘proposition’), (2) the agent asserting it, and (3) the occasion on which the assertion is made.
    Assertions result from acts of interpretation and/or inference, based on information used as evidence."

    Text:
    {text_chunk}

    Task:
    1. Identify and list ONLY the statements that appear to be factual assertions (exclude questions, instructions, etc.).
    2. Return them as a string with each assertion separated by a new line.

    Output:
    """
    )
    
    return LLMChain(
        llm=llm,
        prompt=assertion_prompt
    )


def run_assertion_extraction(assertion_chain, documents, output=False):
    """
    Extracts assertions from a list of documents using an assertion chain.
    Parameters:
        assertion_chain (AssertionChain): The assertion chain to use for extraction.
        documents (list): A list of documents to extract assertions from.
        output (bool, optional): Whether to save the assertions to a file. Defaults to False.
    Returns:
        list: A list of extracted assertions.
    Raises:
        None
    """
    all_assertions = []
    
    if output:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"assertions_{timestamp}.txt"
        file = open(filename, "w", encoding="utf-8")  # Open the file only if output=True

    for i, doc in enumerate(documents):
        text_chunk = doc.page_content

        # (a) Extract assertions
        assertion_result = assertion_chain.run(text_chunk)
        
        # Only save to a file if output=True
        if output:
            file.write(assertion_result + "\n")
        
        # Store them so we can feed them into NER
        split_assertions = assertion_result.split('\n')
        all_assertions.extend(split_assertions)
    
    if output:
        file.close()  # Close the file only if it was opened

    return all_assertions

@click.command()
##ARGUMENTS##
@click.argument("file_path")

##OPTIONS##
@click.option("--output", "-o", is_flag=True, help="Save output to a file.")

def assertion_extraction(file_path:str, output:bool):
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")
    if not os.path.exists(file_path):
        raise ValueError("Path does not exist")
    documents = load_pdf(file_path)
    document_chunks = split_documents(documents)

    #! For testing purposes, only use the first two chunks
    document_chunks = document_chunks[:2]

    llm = ChatOpenAI(model="gpt-4o-mini")
    assertion_chain = create_assertion_extraction_chain(llm)
    run_assertion_extraction(assertion_chain, document_chunks, output=output)