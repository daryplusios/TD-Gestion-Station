from odoo import models, fields, api, _

class Gauging(models.Model):
    _name = 'gauging.gauging'
    _description = 'Fiche de Jaugeage et de Décompte Financier'
    _order = 'date desc'

    name = fields.Char(string='Référence du Rapport', required=True, readonly=True, default=lambda self: _('Nouveau'))
    date = fields.Date(string='Date de l\'Opération', default=fields.Date.context_today, required=True)
    supervisor_id = fields.Many2one('res.users', string='Superviseur Responsable', default=lambda self: self.env.user)
    shift = fields.Selection([('am', 'Groupe Matin (AM)'), ('pm', 'Groupe Soir (PM)')], string='Rotation de Travail', required=True)
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')], default='draft', string='État du Rapport')
    currency_rate = fields.Float(string='Taux de Change (Valeur d\'un Dollar en Gourdes)', default=1.0)

    # Relations principales
    tank_line_ids = fields.One2many('gauging.tank.line', 'gauging_id', string='Lignes d\'Inventaire des Cuves')
    pump_line_ids = fields.One2many('gauging.pump.line', 'gauging_id', string='Relevés des Compteurs de Pompes')
    other_sale_ids = fields.One2many('gauging.other.sale', 'gauging_id', string='Ventes Boutique et Autres')
    coupon_line_ids = fields.One2many('gauging.coupon.line', 'gauging_id', string='Bons de Carburant')
    credit_line_ids = fields.One2many('gauging.credit.line', 'gauging_id', string='Ventes à Crédit')
    check_line_ids = fields.One2many('gauging.check.line', 'gauging_id', string='Détails des Chèques')
    disbursement_ids = fields.One2many('gauging.disbursement', 'gauging_id', string='Décaissements et Dépenses')

    # Grille de décompte des billets
    bill_1000 = fields.Integer(string='Nombre de Billets de 1000 Gourdes')
    bill_500 = fields.Integer(string='Nombre de Billets de 500 Gourdes')
    bill_250 = fields.Integer(string='Nombre de Billets de 250 Gourdes')
    bill_100 = fields.Integer(string='Nombre de Billets de 100 Gourdes')
    bill_50 = fields.Integer(string='Nombre de Billets de 50 Gourdes')
    bill_25 = fields.Integer(string='Nombre de Billets de 25 Gourdes')
    bill_10 = fields.Integer(string='Nombre de Billets de 10 Gourdes')
    coin_amount = fields.Float(string='Montant Total des Monnaies et Pièces')
    cash_usd = fields.Float(string='Montant Total des Dollars Cash (USD)')

    # Terminaux et Subventions
    tpe_unibk = fields.Float(string='Terminal de Paiement UNIBK')
    tpe_sgbk = fields.Float(string='Terminal de Paiement SGBK')
    tpe_bandari = fields.Float(string='Terminal de Paiement Bandari')
    subsidy_amount = fields.Float(string='Montant de la Subvention État')

    # Totaux
    total_sales_expected = fields.Float(string='Total des Ventes Théoriques', compute='_compute_all_totals', store=True)
    total_cash_htg = fields.Float(string='Total du Cash en Gourdes', compute='_compute_all_totals', store=True)
    total_remittance = fields.Float(string='Montant Net Réel Rapporté', compute='_compute_all_totals', store=True)
    difference = fields.Float(string='Écart de Caisse Final', compute='_compute_all_totals', store=True)

    @api.depends('pump_line_ids.amount_sold', 'other_sale_ids.amount', 'bill_1000', 'bill_500', 'bill_250', 
                 'bill_100', 'bill_50', 'bill_25', 'bill_10', 'coin_amount', 'cash_usd', 'currency_rate', 
                 'tpe_unibk', 'tpe_sgbk', 'tpe_bandari', 'subsidy_amount', 'coupon_line_ids.amount', 
                 'credit_line_ids.amount', 'check_line_ids.amount', 'disbursement_ids.amount')
    def _compute_all_totals(self):
        for rec in self:
            # 1. Total Attendu
            rec.total_sales_expected = sum(rec.pump_line_ids.mapped('amount_sold')) + sum(rec.other_sale_ids.mapped('amount'))
            
            # 2. Total Cash HTG
            cash_htg = (rec.bill_1000 * 1000) + (rec.bill_500 * 500) + (rec.bill_250 * 250) + \
                       (rec.bill_100 * 100) + (rec.bill_50 * 50) + (rec.bill_25 * 25) + \
                       (rec.bill_10 * 10) + rec.coin_amount
            rec.total_cash_htg = cash_htg
            
            # 3. Total Réel Remis
            usd_en_htg = rec.cash_usd * rec.currency_rate
            autres_entrees = rec.tpe_unibk + rec.tpe_sgbk + rec.tpe_bandari + rec.subsidy_amount + \
                             sum(rec.coupon_line_ids.mapped('amount')) + \
                             sum(rec.credit_line_ids.mapped('amount')) + \
                             sum(rec.check_line_ids.mapped('amount'))
            sorties = sum(rec.disbursement_ids.mapped('amount'))
            
            # Le cash pris pour les dépenses (sorties) est rajouté au total pour équilibrer la caisse
            rec.total_remittance = cash_htg + usd_en_htg + autres_entrees + sorties
            rec.difference = rec.total_remittance - rec.total_sales_expected

    def action_validate(self):
        self.write({'state': 'validated'})


class GaugingPumpLine(models.Model):
    _name = 'gauging.pump.line'
    _description = 'Ligne de Relevé de Pompe'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    pompiste_id = fields.Many2one('hr.employee', string='Pompiste Responsable')
    pump_name = fields.Char(string='Numéro de la Pompe ou Face')
    product_id = fields.Many2one('product.product', string='Produit Carburant')
    meter_opening = fields.Float(string='Index d\'Ouverture du Compteur')
    meter_closing = fields.Float(string='Index de Fermeture du Compteur')
    price_unit = fields.Float(string='Prix Unitaire du Gallon')
    qty_sold = fields.Float(string='Quantité de Gallons Vendus', compute='_compute_line', store=True)
    amount_sold = fields.Float(string='Montant Total de la Vente', compute='_compute_line', store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price

    @api.depends('meter_opening', 'meter_closing', 'price_unit')
    def _compute_line(self):
        for line in self:
            line.qty_sold = line.meter_closing - line.meter_opening
            line.amount_sold = line.qty_sold * line.price_unit


class GaugingOtherSale(models.Model):
    _name = 'gauging.other.sale'
    _description = 'Ligne de Vente Boutique'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    name = fields.Char(string='Description du Produit', required=True)
    qty = fields.Float(string='Quantité Vendue', default=1.0)
    amount = fields.Float(string='Montant Total de la Vente', required=True)


class GaugingTankLine(models.Model):
    _name = 'gauging.tank.line'
    _description = 'Ligne d\'Inventaire de Cuve'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    tank_name = fields.Char(string='Nom de la Cuve ou du Réservoir')
    product_id = fields.Many2one('product.product', string='Produit Carburant')
    opening_qty = fields.Float(string='Quantité de Gallons à l\'Ouverture')
    closing_qty = fields.Float(string='Quantité de Gallons à la Fermeture')
    net_qty = fields.Float(string='Quantité Finale en Stock', compute='_compute_tank', store=True)

    @api.depends('opening_qty', 'closing_qty')
    def _compute_tank(self):
        for line in self:
            line.net_qty = line.closing_qty


class GaugingCouponLine(models.Model):
    _name = 'gauging.coupon.line'
    _description = 'Ligne de Bon Carburant'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    name = fields.Char(string='Description du Bon')
    qty = fields.Integer(string='Quantité de Bons')
    unit_value = fields.Float(string='Valeur Unitaire du Bon')
    amount = fields.Float(string='Montant Total des Bons', compute='_compute_amount', store=True)

    @api.depends('qty', 'unit_value')
    def _compute_amount(self):
        for line in self:
            line.amount = line.qty * line.unit_value


class GaugingCreditLine(models.Model):
    _name = 'gauging.credit.line'
    _description = 'Ligne de Vente à Crédit'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    customer_name = fields.Char(string='Nom complet du Client')
    reference = fields.Char(string='Référence de la Fiche')
    amount = fields.Float(string='Montant Total du Crédit')


class GaugingCheckLine(models.Model):
    _name = 'gauging.check.line'
    _description = 'Ligne de Chèque'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    bank = fields.Char(string='Banque Émettrice du Chèque')
    amount = fields.Float(string='Montant du Chèque')


class GaugingDisbursement(models.Model):
    _name = 'gauging.disbursement'
    _description = 'Ligne de Sortie de Caisse'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    beneficiary = fields.Char(string='Raison ou Bénéficiaire de la Dépense')
    amount = fields.Float(string='Montant de la Dépense')