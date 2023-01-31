# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from datetime import timedelta


class EventManagement(models.Model):
    _name = 'event.management'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    #************** Campos *********************************************
    state = fields.Selection([('draft', 'Borrador'), ('confirm', 'Confirmado'),
                              ('sale', 'Cotizacion'),
                              ('close', 'Cerrado'), ('cancel', 'Cancelado')],
                             string="Estado", default="draft")
    name = fields.Char('Nombre', readonly=True, copy=False, default="Nuevo Evento")
    ref = fields.Char(string='Número de proforma', readonly=True)
    type_of_event_id = fields.Many2one('event.management.type', string="Tipo de Evento",required=True)
    partner_id = fields.Many2one('res.partner', string="Cliente",required=True)
    date = fields.Date(string="Fecha de Cotización", default=fields.Date.today, required=True)
    start_date = fields.Datetime(string="Fecha de Evento",default=lambda self: fields.datetime.now(),required=True)
    end_date = fields.Datetime(string="Fecha de Finalización", compute="_cal_end_date", readonly=False,required=True)
    cat_person = fields.Integer("Contidad de personas", compute="_get_cant_person", readonly=False, store=True)
    cant_base = fields.Integer("Contidad de personas", related="type_of_event_id.base_cap")
    email = fields.Char("Correo", related="partner_id.email")
    phone = fields.Char("Teléfono", related="partner_id.phone")
    cant_hour = fields.Float("Cantidad de horas", default=2)
    service_line_ids = fields.One2many('event.service.line', 'event_id',string="Descripción del servicio ofertado")
    note = fields.Html('Terminos y Condiciones', default="<h3>Condiciones generales:</h3><p><li>Es necesario realizar reserva de fecha con un deposito de 200 dolares.</li><li>El acuerdo en esta cotizacion es por un servicio de 5 horas.</li><li>El saldo total debe ser cancelado con 7 dias laborales de anticipacion.</li><li>De ser aprobada esta oferta se procedera a relaizar contrato con las condiciones generales.</li><li>Estacionamientos para 3 vehículos en el parqueo principal de la la plaza y acceso a parqueo adicional contiguo a las instalaciones de Zona 7 san Agustin ( se debe pagar 20 cordobas por vehiculo )</li><b><h5>ESTA COTIZACION VALIDA PARA 30 DIAS.</h5></b>")
    price_subtotal = fields.Float(string='Total',compute='_compute_price_subtotal',readonly=True, store=True)
    image = fields.Binary("Imagen", attachment=True,
                          help="Este campo contiene la imagen utilizada como imagen para el evento, limitada a 1080x720px.")
    currency_id = fields.Many2one('res.currency', readonly=True,default=lambda self:self.env.user.company_id.currency_id)
    sale_count = fields.Integer(string='# Cotizaciones', compute="_cal_sale_orders")
    sale_id = fields.Many2one("sale.order", string="Cotizaciones", copy=False)
    suggest = fields.Boolean("Sugerencia", default=False)
    #********************************************************************
    #****** Metodos Computados y Metodos de cambio ************************
    @api.depends('type_of_event_id')
    def _get_cant_person(self):
        for record in self:
            record.cat_person = record.type_of_event_id.base_cap
    def _cal_sale_orders(self):
        for record in self:
            record.sale_count = len(self.env["sale.order"].search([('event_id', '=', record.id)]))

    @api.depends("cant_hour")
    def _cal_end_date(self):
        for record in self:
            record.end_date = record.start_date + timedelta(hours=record.cant_hour)

    @api.depends('service_line_ids', 'service_line_ids.amount_total')
    def _compute_price_subtotal(self):
        total = 0
        for record in self:
            for item in record.service_line_ids:
                total += item.amount_total
            record.price_subtotal = total
    
    @api.onchange("partner_id", "cat_person")
    def show_suggest_buttom(self):
        if self.partner_id and self.cat_person:
            self.suggest = True
        else:
            self.suggest = False
    #**************************************************
    #********************** Sobre escribir Metodos ***************************
    @api.model
    def create(self, values):
        start_date = values['start_date']
        end_date = values['end_date']
        partner_name = self.env['res.partner'].browse(values['partner_id']).name
        event_name = self.env['event.management.type'].browse(
            values['type_of_event_id']).name
        if start_date >= end_date:
            raise UserError(_('La fecha de inicio debe ser anterior a la fecha de finalización'))

        name = '%s-%s' % (partner_name, event_name)
        values['name'] = name
        sequence_code = 'event.order.sequence'
        sequence_number = self.env['ir.sequence'].next_by_code(sequence_code)
        values['ref'] = sequence_number
        res = super(EventManagement, self).create(values)
        return res

    #************* Acciones de Botones **********************
    def action_event_confirm(self):
        self.state = "confirm"

    def action_event_cancel(self):
        self.state = "cancel"

    def action_event_close(self):
        pass

    def action_view_invoice_event(self):
        for record in self:
            search_view_ref = self.env.ref("sale.view_sales_order_filter", False)
            form_view_ref = self.env.ref("sale.view_order_form", False)
            tree_view_ref = self.env.ref("sale.view_order_tree", False)

            return {
                "domain": [("event_id", "=", record.id)],
                "name": "Cotizacion del Evento",
                "res_model": "sale.order",
                "type": "ir.actions.act_window",
                "views": [(tree_view_ref.id, "tree"), (form_view_ref.id, "form")],
                "search_view_id": search_view_ref and [search_view_ref.id],
            }

    def suggest_services(self):
        for record in self:
            lineas_servicios = self.env["event.service.line"]
            res=[]
            for line in record.type_of_event_id.services_list_ids:
                new=lineas_servicios.create({
                    'event_id':record.id,
                    'description':line.description,
                    'service_id':line.service_id.id,
                    'price_unit':line.price_unit,
                    'quantity':(record.cat_person * line.quantity) / record.cant_base,
                })
                res.append(new.id)
            record.service_line_ids=[(6,0,res)]

    def action_event_sale_create(self):
        for record in self:
            sale_id = self.env["sale.order"].create({
                "event_id":record.id,
                "partner_id":record.partner_id.id,
                "validity_date":record.date + timedelta(days=30),
                "date_order":record.date,
                "pricelist_id":1,
                "note":record.note
            })
            record.sale_id = sale_id
            for order_line in self.service_line_ids:
                lines = self.env["sale.order.line"].create({
                    "order_id":sale_id.id,
                    "product_id":order_line.service_id.id,
                    "product_uom_qty":order_line.quantity,
                    "price_unit":order_line.price_unit
                })
            if lines and sale_id: record.state = 'sale'
            search_view_ref = self.env.ref("sale.view_sales_order_filter", False)
            form_view_ref = self.env.ref("sale.view_order_form", False)
            tree_view_ref = self.env.ref("sale.view_order_tree", False)

            return {
                "domain": [("event_id", "=", record.id)],
                "name": "Cotizacion del Evento",
                "res_model": "sale.order",
                "type": "ir.actions.act_window",
                "views": [(tree_view_ref.id, "tree"), (form_view_ref.id, "form")],
                "search_view_id": search_view_ref and [search_view_ref.id],
            }
    
    #******************************************************

class EventServiceLine(models.Model):
    _name = 'event.service.line'

    service_id = fields.Many2one('product.product', string="Servicio",required=True)
    price_unit = fields.Float("Precio", related="service_id.list_price", readonly=False)
    quantity = fields.Float("Cantidad")
    description = fields.Text("Descripción",required=True)
    event_id = fields.Many2one('event.management', string="Evento")
    event_type_id = fields.Many2one('event.management.type', string="Tipo de evento")
    amount_total = fields.Float(string="Total", compute="_cal_total")
    currency_id = fields.Many2one('res.currency', readonly=True,default=lambda self:self.env.user.company_id.currency_id)

    @api.onchange("service_id")
    def _get_description(self):
        if not self.service_id: return
        product = self.service_id.with_context(lang=self.event_id.partner_id.lang,)
        self.description = product.get_product_multiline_description_sale()
        self.quantity = 1.0
    
    @api.depends("price_unit", "quantity")
    def _cal_total(self):
        total = 0
        for rec in self:
            total = rec.quantity * rec.price_unit
            rec.amount_total = total
class EventManagementType(models.Model):
    _name = 'event.management.type'

    name = fields.Char(string="Nombre", required=True)
    image = fields.Binary("Imagen", attachment=True,help="Este campo contiene la imagen utilizada como imagen para el evento, limitada a 1080x720px.")
    event_count = fields.Integer(string="# Eventos",compute='_compute_event_count')
    base_cap = fields.Integer("Capacidad base de personas", required=True)
    services_list_ids = fields.One2many("event.service.line", 'event_type_id', string="Lista de servicios para este evento")
    base_cost = fields.Float("Costo base",compute="_compute_base_cost",required=True)

    @api.depends('services_list_ids', 'services_list_ids.amount_total')
    def _compute_base_cost(self):
        total = 0
        for record in self:
            for item in record.services_list_ids:
                total += item.amount_total
            record.base_cost = total

    def _compute_event_count(self):
        for records in self:
            events = self.env['event.management'].search([
                ('type_of_event_id', '=', records.id)])
            records.event_count = len(events)

    def _get_action(self, action_xml_id):
        action = self.env['ir.actions.actions']._for_xml_id(action_xml_id)
        if self:
            action['display_name'] = self.display_name
        context = {
            'search_default_type_of_event_id': [self.id],
            'default_type_of_event_id': self.id,
        }

        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context
        return action

    def get_event_type_action_event(self):
        return self._get_action(
            'event_management.event_management_action_view_kanban')

class SaleOrder(models.Model):
    _inherit="sale.order"

    event_id = fields.Many2one("event.management", string="Evento")