import win32com.client

from .command_builder import CommandBuilder

class MinitabRunner:

    def __init__(self, config):
        self.config = config
        self.app = win32com.client.DispatchEx("Mtb.Application")

    def run(self, data_path):

        project = self.app.ActiveProject
        project.Open(data_path)

        cmd_builder = CommandBuilder(self.config)
        commands = cmd_builder.build()

        project.ExecuteCommand(commands)