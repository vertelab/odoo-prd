import openpyxl
import base64
from io import BytesIO
import re

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
 
    # def import_excel(self):
    #     """
    #     Läser en excel-fil (kravspecifikation) och skapar krav i prd.requirement.
    #     """
    #     try:
    #         wb = openpyxl.load_workbook(filename=BytesIO(base64.b64decode(self.file)),data_only=True)
    #     except Exception as e:
    #         raise UserError(_("Kunde inte läsa Excel-filen: %s") % e)

    #     requirement_model = self.env['prd.requirement']
    #     created_count = 0

    #     prd_id = self.env.context['active_id']

    #     # Gå igenom varje blad i boken
    #     for sheet in wb.worksheets:
    #         _logger.warning(f"{sheet=}")
    #         current_page = sheet.title.strip()
    #         self.get_ids(sheet)
    #         for row in sheet.iter_cols(values_only=True,max_row=1):
                
    #             if not row or not row[0]:
    #                 continue
            
    # def get_ids(self,sheet):
    #     for test in sheet.iter_cols(values_only=True,max_col=0):
    #         _logger.error(f"{test=}")
        # _logger.error(sheet.iter_rows(values_only=True).values)
         

    def import_excel(self):
        """
        Läser en excel-fil (kravspecifikation) och skapar krav i prd.requirement.
        """
        try:
            wb = openpyxl.load_workbook(filename=BytesIO(base64.b64decode(self.file)),data_only=True)
            # ~ wb = openpyxl.load_workbook(self.file, data_only=True)
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

            for row in sheet.iter_rows(values_only=True):
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
                    req_type = self.create_req_type(current_page,desc)
                    priority = self.get_priority(row)
                    category = self.get_category(row,is_category)

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
                    # _logger.warning(f"{values=}")
                    
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
                category = Command.link(category_id.id)
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

    def create_req_type(self,curent_page,desc):
        req_type = self.env["prd.requirement_type"]

        req_type_id = req_type.search([("name", "=", curent_page),("description", "=", desc)],limit=1)

        if not req_type_id:
            req_type_id = req_type.create({
                "name": curent_page,
                "description": desc
            })
        return req_type_id

    def check_row_len(self,row,row_index,max_len,min_len):
        check = str(row[row_index]).strip() if len(row) > row_index and row[row_index] and len(row[row_index]) <= max_len and len(row[row_index]) >= min_len else False
        return check

    def Ximport_excel(self):

            wb = openpyxl.load_workbook(filename=BytesIO(base64.b64decode(self.file)))
            
            # ~ raise UserError(f"{wb.sheetnames=}")
            for ws in wb.sheetnames:
                activews = wb[ws]
                record = {}                
                for row in range(1, activews.max_row + 1):
                    value = activews.cell(row=row,column=1).value
                    if value and any(c.isdigit() for c in str(value)): # Has numbers
                        record = {
                            'page': ws,
                            'no': activews.cell(row=row,column=1),
                             'category':  activews.cell(row=row,column=2).value if len(activews.cell(row=row,column=2).value) < 25 else '',
                             'name': activews.cell(row=row,column=2) if len(activews.cell(row=row,column=2).value) > 25 else activews.cell(row=row,column=3).value ,
                            'prd_id': self.env.context['active_id'],
                        
                        }
                        self.env['prd.requirement'].create(record)

                    # ~ if activews.cell(row=row,column=1) != None:
                        # ~ for col in range(1, 13):
                            # ~ record_value = activews.cell(row=row, column=col).value
                            # ~ if record_value != None:
                                # ~ record_value = str(record_value).strip()
                                # ~ record_value = record_value.lower()
                                # ~ if record_value == "monerary":
                                    # ~ record_value = "monetary"
                                # ~ if "percentage" in record_value:
                                    # ~ record_value = record_value.replace("percentage", "percent")
                            # ~ record[self.field_keys[col-1]] = record_value
                        # ~ record['csrd_sheet_name'] = ws
                        # ~ self.create_record(record)
            # ~ return {
                # ~ 'type': 'ir.actions.client',
                # ~ 'tag': 'reload',
            # ~ }
