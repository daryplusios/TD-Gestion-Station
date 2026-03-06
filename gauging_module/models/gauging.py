from odoo import models, fields, api, _

class Gauging(models.Model):
    _name = 'gauging.gauging'
    _description = 'Fiche de Jaugeage et Décompte'
    _order = 'date desc'

    # Informations d'en-tête (UX descriptive)
    name = fields.Char(string='Référence du Rapport', required=True, readonly=True, default=lambda self: _('Nouveau'))
    date = fields.Date(string='Date de l\'Opération', default=fields.Date.context_today, required=True)
    supervisor_id = fields.Many2one('res.users', string='Superviseur Responsable', default=lambda self: self.env.user)
    shift = fields.Selection([('am', 'Groupe AM (Matin)'), ('pm', 'Groupe PM (Soir)')], string='Rotation / Shift', required=True)
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')], default='draft', string='État')
    currency_rate = fields.Float(string='Taux de Change (1 USD = X HTG)', default=1.0)

    # Relations principales
    tank_line_ids = fields.One2many('gauging.tank.line', 'gauging_id', string='Lignes d\'Inventaire Cuves')
    pump_line_ids = fields.One2many('gauging.pump.line', 'gauging_id', string='Relevés des Pompes')
    disbursement_ids = fields.One2many('gauging.disbursement', 'gauging_id', string='Décaissements / Sorties')
    coupon_line_ids = fields.One2many('gauging.coupon.line', 'gauging_id', string='Bons de Carburant')
    credit_line_ids = fields.One2many('gauging.credit.line', 'gauging_id', string='Ventes à Crédit')
    check_line_ids = fields.One2many('gauging.check.line', 'gauging_id', string='Chèques Reçus')

    # Décompte des billets HTG (Détail exact de la Photo 4)
    bill_1000 = fields.Integer(string='Billets de 1000 Gds')
    bill_500 = fields.Integer(string='Billets de 500 Gds')
    bill_250 = fields.Integer(string='Billets de 250 Gds')
    bill_100 = fields.Integer(string='Billets de 100 Gds')
    bill_50 = fields.Integer(string='Billets de 50 Gds')
    bill_25 = fields.Integer(string='Billets de 25 Gds')
    bill_10 = fields.Integer(string='Billets de 10 Gds')
    coin_amount = fields.Float(string='Montant Monnaies / Pièces')
    cash_usd = fields.Float(string='Cash en USD')

    # Banques et Subvention (Photo 4)
    tpe_unibk = fields.Float(string='TPE UNIBK')
    tpe_sgbk = fields.Float(string='TPE SGBK')
    tpe_bandari = fields.Float(string='TPE Bandari')
    subsidy_amount = fields.Float(string='Montant Subvention')

    # Totaux Stockés
    total_sales_expected = fields.Float(string='Ventes Attendues', compute='_compute_all_totals', store=True)
    total_cash_htg = fields.Float(string='Total Cash HTG', compute='_compute_all_totals', store=True)
    total_remittance = fields.Float(string='Total Réel Remis', compute='_compute_all_totals', store=True)
    difference = fields.Float(string='Écart (Short/Over)', compute='_compute_all_totals', store=True)

    @api.depends('pump_line_ids.amount_sold', 'bill_1000', 'bill_500', 'bill_250', 'bill_100', 'bill_50', 
                 'bill_25', 'bill_10', 'coin_amount', 'cash_usd', 'currency_rate', 'tpe_unibk', 
                 'tpe_sgbk', 'tpe_bandari', 'subsidy_amount', 'coupon_line_ids.amount', 
                 'credit_line_ids.amount', 'check_line_ids.amount', 'disbursement_ids.amount')
    def _compute_all_totals(self):
        for rec in self:
            # 1. Total théorique des ventes
            rec.total_sales_expected = sum(rec.pump_line_ids.mapped('amount_sold'))
            # 2. Total Cash Gourdes
            htg = (rec.bill_1000 * 1000) + (rec.bill_500 * 500) + (rec.bill_250 * 250) + \
                  (rec.bill_100 * 100) + (rec.bill_50 * 50) + (rec.bill_25 * 25) + \
                  (rec.bill_10 * 10) + rec.coin_amount
            rec.total_cash_htg = htg
            # 3. Total Réel (Cash + USD + TPE + Bons + Crédits + Subvention - Dépenses)
            others = rec.tpe_unibk + rec.tpe_sgbk + rec.tpe_bandari + rec.subsidy_amount + \
                     sum(rec.coupon_line_ids.mapped('amount')) + \
                     sum(rec.credit_line_ids.mapped('amount')) + \
                     sum(rec.check_line_ids.mapped('amount'))
            usd_in_htg = rec.cash_usd * rec.currency_rate
            out_money = sum(rec.disbursement_ids.mapped('amount'))
            rec.total_remittance = (htg + usd_in_htg + others) - out_money
            # 4. Écart final
            rec.difference = rec.total_remittance - rec.total_sales_expected

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouveau')) == _('Nouveau'):
            vals['name'] = self.env['ir.sequence'].next_by_code('gauging.gauging') or _('Nouveau')
        return super(Gauging, self).create(vals)

    def action_validate(self):
        self.write({'state': 'validated'})

class GaugingPumpLine(models.Model):
    _name = 'gauging.pump.line'
    _description = 'Ligne de Pompe'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    pompiste_id = fields.Many2one('hr.employee', string='Pompiste')
    pump_name = fields.Char(string='Pompe / Face')
    product_id = fields.Many2one('product.product', string='Produit')
    meter_opening = fields.Float(string='Ouverture Miteur')
    meter_closing = fields.Float(string='Fermeture Miteur')
    calibration_qty = fields.Float(string='Calibrage (Retour Cuve)')
    price_unit = fields.Float(string='Prix Unitaire', related='product_id.list_price', store=True)
    qty_sold = fields.Float(string='Gallons Vendus', compute='_compute_pump', store=True)
    amount_sold = fields.Float(string='Montant Vente', compute='_compute_pump', store=True)

    @api.depends('meter_opening', 'meter_closing', 'calibration_qty', 'price_unit')
    def _compute_pump(self):
        for line in self:
            line.qty_sold = line.meter_closing - line.meter_opening - line.calibration_qty
            line.amount_sold = line.qty_sold * line.price_unit

class GaugingTankLine(models.Model):
    _name = 'gauging.tank.line'
    _description = 'Stock Cuve'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    tank_name = fields.Char(string='Nom de la Cuve')
    product_id = fields.Many2one('product.product', string='Produit')
    opening_qty = fields.Float(string='Ouverture Stock')
    closing_qty = fields.Float(string='Fermeture Stock')
    net_qty = fields.Float(string='Gallons en Stock', compute='_compute_tank', store=True)

    @api.depends('opening_qty', 'closing_qty')
    def _compute_tank(self):
        for line in self:
            line.net_qty = line.closing_qty

class GaugingDisbursement(models.Model):
    _name = 'gauging.disbursement'
    _description = 'Sortie de Caisse'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    beneficiary = fields.Char(string='À qui / Raison')
    authorized_by = fields.Char(string='Autorisé par')
    amount = fields.Float(string='Montant Décaissé')

class GaugingCouponLine(models.Model):
    _name = 'gauging.coupon.line'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    name = fields.Selection([('national', 'Bon National'), ('total', 'Bon Total')], string='Type de Bon')
    qty = fields.Integer(string='Quantité')
    unit_value = fields.Float(string='Valeur')
    amount = fields.Float(string='Montant Total', compute='_compute_amount', store=True)

    @api.depends('qty', 'unit_value')
    def _compute_amount(self):
        for line in self:
            line.amount = line.qty * line.unit_value

class GaugingCreditLine(models.Model):
    _name = 'gauging.credit.line'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    customer_name = fields.Char(string='Nom du Client')
    invoice_ref = fields.Char(string='N° Fiche Crédit')
    product_id = fields.Many2one('product.product', string='Produit')
    qty = fields.Float(string='Qté Gallons')
    amount = fields.Float(string='Montant Crédit')

class GaugingCheckLine(models.Model):
    _name = 'gauging.check.line'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    bank_name = fields.Char(string='Banque')
    amount = fields.Float(string='Montant Chèque')