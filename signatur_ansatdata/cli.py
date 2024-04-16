"""CLI interface for signatur_ansatdata project.

Be creative! do whatever you want!

- Install click or typer and create a CLI app
- Use builtin argparse
- Start a web application
- Import things from your .base module
"""

from signatur_ansatdata.base import hello_world, SBSYSClient


def main():  # pragma: no cover
    """
    The main function executes on commands:
    `python -m signatur_ansatdata` and `$ signatur_ansatdata `.

    This is your program's entry point.

    You can change this function to do whatever you want.
    Examples:
        * Run a test suite
        * Run a server
        * Do some other stuff
        * Run a command line application (Click, Typer, ArgParse)
        * List all available tasks
        * Run an application (Flask, FastAPI, Django, etc.)
    """

    client = SBSYSClient(base_url="https://sbsysapi.randers.dk", api_key="")
    # Define your JSON data
    json_data = {
        "PrimaerPerson": {
            "CprNummer": "200395-xxxx"
        },
        "SagsTyper": [
            {
                "Id": 5
            }
        ]
    }

    # Call the journalise_file_personalesag method with the JSON data
    response = client.search_cases(json_data)

    if response:
        print("Search results:")
        print(response)
    else:
        print("Failed to retrieve search results")
    hello_world()

