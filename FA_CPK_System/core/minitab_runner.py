import win32com.client,os
class MinitabRunner:
    def __init__(self,c):
        self.output=c['minitab']['output_dir']
        os.makedirs(self.output,exist_ok=True)
        self.app=win32com.client.Dispatch('Mtb.Application')
        # self.project = self.app.NewProject()
        # self.app.Visible=True

    def run_cpk(self,data):
        for item,i in data.items():
            print(item, i)
            # ws=self.app.ActiveProject.Worksheets.Add()
            ws = self.project.Worksheets.Add()
            print(ws)
            for idx,v in enumerate(i['values']): ws.Cells(idx+1,1).Value=v
            cmd = f"Capability C1; LSL {i['lsl']}; USL {i['usl']}."

            # self.project.ExecuteCommand(cmd)
            self.project.ExecuteCommand(cmd)
            # ✅ 导出图
            outfile = os.path.join(self.output, f"{item}.png")
            self.project.Commands.Item(self.app.ActiveProject.Commands.Count).Outputs.Item(1).Export(outfile)
            # print(idx, v)
            # self.app.ExecuteCommand(f"Capability C1; LSL {i['lsl']}; USL {i['usl']}.")
            # self.app.ActiveProject.Commands.Item(self.app.ActiveProject.Commands.Count).Outputs.Item(1).Export(os.path.join(self.output,f"{item}.png"))

    def run_grr(self,data):
        for item,i in data.items():
            ws=self.app.ActiveProject.Worksheets.Add()
            for idx,v in enumerate(i['values']): ws.Cells(idx+1,1).Value=v
            self.app.ExecuteCommand("GageRRStudy C1; Parts 10; Operators 3.")
            self.app.ActiveProject.Commands.Item(self.app.ActiveProject.Commands.Count).Outputs.Item(1).Export(os.path.join(self.output,f"{item}_GRR.png"))
