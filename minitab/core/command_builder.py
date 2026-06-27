import os

class CommandBuilder:

    def __init__(self, config):
        self.config = config

    def build(self):

        usl = self.config["spec"]["USL"]
        lsl = self.config["spec"]["LSL"]
        target = self.config["spec"]["TARGET"]

        image_dir = self.config["paths"]["images"]

        cpk_img = os.path.join(image_dir, "cpk.jpg").replace("\\", "/")
        grr_img = os.path.join(image_dir, "grr.jpg").replace("\\", "/")

        commands = f"""
        Normtest C1;
          AD.

        Capability C1;
          USL {usl};
          LSL {lsl};
          Target {target};
          Overall.

        GSAVE "{cpk_img}";
          JPEG.

        GageRR C1 C2 C3;
          StudyVar 6;
          Parts 10;
          Operators 3.

        GSAVE "{grr_img}";
          JPEG.
        """

        return commands