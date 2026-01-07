from agents.base import BaseAgent
class GenerationAgent(BaseAgent):
    phase = "generation"

    SYSTEM_PROMPT = """
You are the GENERATION agent.
Your job is to produce an initial output based on the user’s request.
Only use the allowed tools for this phase.

Tools: add_numbers(a, b)
"""

    MAIN_PROMPT = """
GenerationAgent received: {prompt}You are a test engineer. Based on the following description of the feature, create detailed test steps.
 ---------------------------------------------------
   Requirement 
   {{REQUIREMENT}}
 MANDATORY if  ##NEW## text is mentioned in acceptance criteria pointer then create test case for only those acceptance criteria pointers else Create individual test case for each acceptance criteria pointers provided in user story.
 MANDATORY if acceptance criteria didnt mentioned create test case based on user requirement. 
 --------------------------------------------------- 
   RULES
   %locator% - replace with locator within single quotes (ex: Click on the %locator% -> Click on the 'User link')
   %data% within double quotes (ex: Enter the %locator% as "%data%" -> Enter the 'Comments' as "test comment")
   Test Case: <test case description>
   File Name: <test case file name>
   FileName should create without any white space or special characters
 <<END>> at the end of each test case
   NO Step numbers
   Do not add any comments are notes other then output format requested.
   DO not change output format and do not add any * symbols in output
   DO Not create any step with '%locator%' or "%data%". instead of the please add actual data or loctor name.
   Its MANDATORY to add Launch step for each test case. 
 Use steps from the prompt templates and data values from the reference test cases while constructing each step.
 For every step, follow these mapping rules:
 
 Choose the most suitable step from the ACTIONS section.
 
 Replace %locator% using locator names derived from the Requirement or from the step templates, enclosed in single quotes.
 
 Replace %data% with data values from RAG_TESTCASES, enclosed in double quotes.
 
 Do not leave any %locator% or %data% unresolved.
 
 Keep the exact sentence structure from the template.
 Ensure each test case starts with a Launch step and follows the logical order from the reference examples.
 Combine the template actions, locators, and data values to form realistic, executable steps.
 --------------------------------------------------
   Please follow below output format: 
   Test Case: <test case description>
   File Name: <test case file name>
   \n
 <Step1>
 <Step2>
 <Stepn>
 <<END>>
   Based on test case count you can display all test cases in same format mention above do not add any additional content or statement in output. 
 ---------------------------------------------------
   *** TEST STEP TEMPLATE STARTS ***
   {{ACTIONS}}
   *** TEST STEP TEMPLATE ENDS ***
 ---------------------------------------------------
   *** REFERENCE TESTS START *** 
   {{RAG_TESTCASES}}
 
   *** REFERENCE TESTS END ***
      Determine the appropriate number of test cases based on the complexity of the requirement and based on the requirement above by following the rules. For each test step, associate the best possible template by using the template and reference tests. Use the template exactly as described."""




    def run(self, prompt: str) -> str:
        context = self.SYSTEM_PROMPT + "\n" + self.MAIN_PROMPT.format(user_prompt=prompt)
        return context
