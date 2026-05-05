import openpyxl
import base64
from io import BytesIO
import re
import zipfile

from datetime import datetime, timedelta 
from odoo import api, fields, models, _
from odoo.fields import Command
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class ExcelWizard(models.TransientModel):
    _name = 'prd.excel.wizard'
    _description = 'Load Requirements from Excel'

    file = fields.Binary(string="File", required=True)

    def import_excel(self):
        """
        Läser en excel-fil (kravspecifikation) och skapar krav i prd.requirement.
        """
        file = BytesIO(base64.b64decode(self.file))
        try:
            wb = openpyxl.load_workbook(filename=file,data_only=True)
        except ValueError as e:
            if "Unable to read workbook" in str(e):
                wb = self.fix_broken_excel(file)
        except Exception as e:
            raise UserError(_("Kunde inte läsa Excel-filen: %s") % e)

        requirement_model = self.env['prd.requirement']
        created_count = 0

        prd_id = self.env.context['active_id']

        # Gå igenom varje blad i boken
        for sheet in wb.worksheets:
            current_page = sheet.title.strip()
            # _logger.warning(f"{sheet=}")
            # if current_page != "2. Redovisning":
            #     continue

            for row in sheet.iter_rows(values_only=True,max_col=20,max_row=1000):
                if not row or not row[0]:
                    continue
                first_cell = self.find_code(row)
                # _logger.warning(f"{row=} {first_cell=}")
                # Identifiera kravnummer (1.1, 2.1.5 etc.)
                
                if first_cell and any(c.isdigit() for c in first_cell):
                    
                    is_category = self.check_row_len(row,row_index=2,max_len=9999,min_len=26)
                    code = first_cell
                    desc = self.get_description(row,is_category)
                    name = desc
                    req_type = self.create_req_type(current_page,desc,prd_id)
                    priority = self.get_priority(row)
                    category = self.get_category(row,is_category)

                    # SMART TRUNKERING:
                    # 1. Om desc är längre än 150 tecken, korta av
                    # 2. Försök klippa vid sista punkten eller mellanslaget om möjligt
                    max_len = 100
                    if desc and len(desc) > max_len:
                        # Försök hitta en punkt inom de första 150 tecknen
                        snippet = desc[:max_len]
                        if '.' in snippet:
                            name = snippet.rsplit('.', 1)[0] + "."
                        else:
                            name = snippet.strip() + "..."
                    else:
                        name = desc

                    # Skapa requirement-posten
                    values = {
                        'code': code,
                        'name': name or desc or "Unnamed Requirement",
                        'description': desc or '',
                        'category': [category] if category else False,
                        'priority': priority,
                        'prd_id': prd_id,
                        'req_type': req_type.id if req_type else False
                    }
                    _logger.warning(f"{values=}")
                    
                    requirement_model.create(values)

                    # _logger.error(f"We did create the values..."*10)
                    # created_count += 1
                    # break
        return

    def get_priority(self,row):
        priority_cell = " ".join(map(str, row)).lower()
        priority = ""
        # Bedöm prioritet
        if "ska" in priority_cell:
            priority = 'must'
        elif "bör" in priority_cell or "br" in priority_cell:
            priority = 'should'
        elif "could" in priority_cell:
            priority = 'could'
        else:
            priority = 'must'
        return priority

    def find_code(self,row):
        code = str(row[0]).strip()
        return code

    def get_category(self,row,is_category):
        category_str = self.check_row_len(row,row_index=1,max_len=25,min_len=1)
        category = False
        if category_str and is_category:
            category_id = self.env["prd.requirement_category"].search([("name", "=", category_str)],limit=1)
            if category_id:
                category = Command.link(category_id.id) # type: ignore
            else:
                category = Command.create({
                    "name": category_str
                })
        return category

    def get_description(self,row,is_category):
        desc = self.check_row_len(row,row_index=1,max_len=9999,min_len=1)
        if not desc and is_category:
            desc = self.check_row_len(row,row_index=2,max_len=9999,min_len=26)
        return desc

    def create_req_type(self,curent_page,desc,prd_id):
        req_type = self.env["prd.requirement_type"]

        req_type_id = req_type.search([("name", "ilike", curent_page),("prd_id", "=", prd_id)],limit=1)

        if not req_type_id:
            _logger.error(f"{prd_id=}")
            req_type_id = req_type.create({
                "name": curent_page,
                "prd_id": prd_id
            }) # type: ignore
        return req_type_id

    def check_row_len(self,row,row_index,max_len,min_len):
#        check = str(row[row_index]).strip() if len(row) > row_index and row[row_index] and len(row[row_index]) <= max_len and len(row[row_index]) >= min_len else False
         # NY SÄKER KOD (ersätt rad 133):
         if len(row) > row_index and row[row_index] is not None:
             str_value = str(row[row_index]).strip()
             # kolla längd
             if len(str_value) <= max_len and len(str_value) >= min_len:
                 return str_value
         else:
             check = False

#        return check

    def fix_broken_excel(self,file):
        try:
            new_file = BytesIO()
            with zipfile.ZipFile(file, 'r') as zin:
                with zipfile.ZipFile(new_file, 'w') as zout:
            
                    for item in zin.infolist():
                        buffer = zin.read(item.filename)
                        
                        if item.filename == 'xl/workbook.xml':
                            xml_str = buffer.decode('utf-8')
                            
                            clean_xml = re.sub(r'<definedNames>.*?</definedNames>', '', xml_str, flags=re.DOTALL)
                            
                            if len(xml_str) != len(clean_xml):
                                _logger.warning(" -> Found and removed broken <definedNames> tag.")
                            
                            zout.writestr(item, clean_xml)
                        
                        else:
                            zout.writestr(item, buffer)
            wb = openpyxl.load_workbook(filename=new_file,data_only=True)
        except Exception as e:
            raise UserError(f"Tried to fix broken Excel but failed: {e}")
        return wb

