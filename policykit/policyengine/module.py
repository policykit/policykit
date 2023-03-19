import json
import os
from policyengine.models import (
    Procedure,
)

class PolicyTemplateFactory():

    
    def build_procedure_templates(restart=False):
        """
            Create procedute templates for a given platform
        """
        if restart:
            Procedure.objects.all().delete()
        
        cur_path = os.path.abspath(os.path.dirname(__file__))
        procedure_path = os.path.join(cur_path, f"../policytemplates/procedures.json")
        with open(procedure_path) as f:
            procedure_data = json.loads(f.read())
            for procedure in procedure_data:
                procedure["variables_dict"] = json.dumps(procedure["variables_dict"])
                Procedure.objects.create(**procedure)

        
        

        