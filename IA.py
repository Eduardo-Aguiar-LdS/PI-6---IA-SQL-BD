from premsql.agents import BaseLineAgent
from premsql.generators import Text2SQLGeneratorOllama
from premsql.agents.tools import SimpleMatplotlibTool
from premsql.executors import SQLiteExecutor

text2_sqlmodel = Text2SQLGeneratorHF(
    model_or_name_or_path="prem-research/prem-1B-SQL",
    experiment_name="test_generators",
    device="cuda:0",
    type="test"
)

analyser_and_plotter = Text2SQLGeneratorHF(
    model_or_name_or_path="meta-llama/Llama-3.2-1B-Instruct",
    experiment_name="test_generators",
    device="cuda:0",
    type="test"
)

agent = BaseLineAgent(
    session_name="testing_hf",
    db_connection_uri="sqlite:////db/biblioteca.sqlite",
    specialized_model1=model,
    specialized_model2=model,
    plot_tool=SimpleMatplotlibTool(),
    executor=SQLiteExecutor()
)

response = agent(
    "/query what all tables are present inside the database"
)
response.show_dataframe()
