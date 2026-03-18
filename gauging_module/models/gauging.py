from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Gauging(models.Model):
    _name = 'gauging.gauging'
    _description = 'Fiche de Jaugeage et de Décompte Financier'
    _order = 'date desc'

    name = fields.Char(string='Référence du Rapport', required=True, copy=False, default=lambda self: _('Nouveau'))
    date = fields.Date(string='Date de l\'Opération', default=fields.Date.context_today, required=True)
    supervisor_id = fields.Many2one('res.users', string='Superviseur Responsable', default=lambda self: self.env.user)
    shift = fields.Selection([('am', 'Groupe Matin (AM)'), ('pm', 'Groupe Soir (PM)')], string='Rotation de Travail', required=True)
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')], default='draft', string='État du Rapport')
    currency_rate = fields.Float(string='Taux de Change (Valeur d\'un Dollar en Gourdes)', default=1.0)

    # Relations
    tank_line_ids = fields.One2many('gauging.tank.line', 'gauging_id', string='Lignes d\'Inventaire des Cuves')
    pump_line_ids = fields.One2many('gauging.pump.line', 'gauging_id', string='Relevés des Compteurs de Pompes')
    coupon_line_ids = fields.One2many('gauging.coupon.line', 'gauging_id', string='Bons de Carburant')
    credit_line_ids = fields.One2many('gauging.credit.line', 'gauging_id', string='Ventes à Crédit')
    check_line_ids = fields.One2many('gauging.check.line', 'gauging_id', string='Détails des Chèques')
    disbursement_ids = fields.One2many('gauging.disbursement', 'gauging_id', string='Décaissements et Dépenses')

    # Billets et Monnaie
    bill_1000 = fields.Integer(string='Billets de 1000 Gourdes')
    bill_500 = fields.Integer(string='Billets de 500 Gourdes')
    bill_250 = fields.Integer(string='Billets de 250 Gourdes')
    bill_100 = fields.Integer(string='Billets de 100 Gourdes')
    bill_50 = fields.Integer(string='Billets de 50 Gourdes')
    bill_25 = fields.Integer(string='Billets de 25 Gourdes')
    bill_10 = fields.Integer(string='Billets de 10 Gourdes')
    coin_amount = fields.Float(string='Montant Monnaies')
    cash_usd = fields.Float(string='Dollars Cash (USD)')

    # Terminaux et Subventions
    tpe_unibk = fields.Float(string='Terminal UNIBK')
    tpe_sgbk = fields.Float(string='Terminal SGBK')
    tpe_bandari = fields.Float(string='Terminal Bandari')
    subsidy_amount = fields.Float(string='Montant Subvention État')

    # Nouveaux totaux visuels instantanés
    total_tpe = fields.Float(string='Total Cartes (TPE)', compute='_compute_live_totals', store=True)
    total_usd_htg = fields.Float(string='Équivalent USD en Gourdes', compute='_compute_live_totals', store=True)

    # Totaux de réconciliation
    total_sales_expected = fields.Float(string='Total des Ventes Théoriques', compute='_compute_all_totals', store=True)
    total_cash_htg = fields.Float(string='Total du Cash en Gourdes', compute='_compute_all_totals', store=True)
    total_remittance = fields.Float(string='Montant Net Réel Rapporté', compute='_compute_all_totals', store=True)
    difference = fields.Float(string='Écart de Caisse Final', compute='_compute_all_totals', store=True)

    @api.depends('tpe_unibk', 'tpe_sgbk', 'tpe_bandari', 'cash_usd', 'currency_rate')
    def _compute_live_totals(self):
        for rec in self:
            rec.total_tpe = rec.tpe_unibk + rec.tpe_sgbk + rec.tpe_bandari
            rec.total_usd_htg = rec.cash_usd * rec.currency_rate

    @api.depends('pump_line_ids.amount_sold', 'bill_1000', 'bill_500', 'bill_250', 
                 'bill_100', 'bill_50', 'bill_25', 'bill_10', 'coin_amount', 'cash_usd', 'currency_rate', 
                 'tpe_unibk', 'tpe_sgbk', 'tpe_bandari', 'subsidy_amount', 'coupon_line_ids.amount', 
                 'credit_line_ids.amount', 'check_line_ids.amount', 'disbursement_ids.amount')
    def _compute_all_totals(self):
        for rec in self:
            rec.total_sales_expected = sum(rec.pump_line_ids.mapped('amount_sold'))
            
            cash_htg = (rec.bill_1000 * 1000) + (rec.bill_500 * 500) + (rec.bill_250 * 250) + \
                       (rec.bill_100 * 100) + (rec.bill_50 * 50) + (rec.bill_25 * 25) + \
                       (rec.bill_10 * 10) + rec.coin_amount
            rec.total_cash_htg = cash_htg
            
            usd_en_htg = rec.cash_usd * rec.currency_rate
            autres_entrees = rec.tpe_unibk + rec.tpe_sgbk + rec.tpe_bandari + rec.subsidy_amount + \
                             sum(rec.coupon_line_ids.mapped('amount')) + \
                             sum(rec.credit_line_ids.mapped('amount')) + \
                             sum(rec.check_line_ids.mapped('amount'))
            sorties = sum(rec.disbursement_ids.mapped('amount'))
            
            rec.total_remittance = cash_htg + usd_en_htg + autres_entrees + sorties
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
    _description = 'Ligne de Relevé de Pompe'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    pompiste_id = fields.Many2one('hr.employee', string='Pompiste Responsable')
    pump_name = fields.Char(string='Numéro de la Pompe ou Face')
    product_id = fields.Many2one('product.product', string='Produit Carburant')
    meter_opening = fields.Float(string='Index d\'Ouverture', digits=(16, 3))
    meter_closing = fields.Float(string='Index de Fermeture', digits=(16, 3))
    price_unit = fields.Float(string='Prix Unitaire du Gallon')
    qty_sold = fields.Float(string='Quantité de Gallons Vendus', compute='_compute_line', store=True, digits=(16, 3))
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

class GaugingTankLine(models.Model):
    _name = 'gauging.tank.line'
    _description = 'Ligne d\'Inventaire de Cuve'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    tank_name = fields.Selection([
        ('Super Tank 1', 'Super Tank 1 (Gazoline)'),
        ('Super Tank 2', 'Super Tank 2 (Gazoline)'),
        ('Diesel Tank 3', 'Diesel Tank 3'),
        ('Diesel Tank 4', 'Diesel Tank 4'),
        ('Super Tank 5', 'Super Tank 5 (Gazoline)'),
        ('Super Tank 6', 'Super Tank 6 (Gazoline)'),
        ('Propane Tank 1', 'Propane Tank 1'),
        ('Propane Tank 2', 'Propane Tank 2'),
    ], string='Nom de la Cuve', required=True)
    opening_qty = fields.Float(string='Quantité Ouverture', digits=(16, 3))
    closing_qty = fields.Float(string='Quantité Fermeture', digits=(16, 3))
    qty_sold = fields.Float(string='Quantité Vendue', compute='_compute_tank', store=True, digits=(16, 3))

    @api.depends('opening_qty', 'closing_qty')
    def _compute_tank(self):
        for line in self:
            line.qty_sold = line.opening_qty - line.closing_qty

class GaugingCouponLine(models.Model):
    _name = 'gauging.coupon.line'
    _description = 'Ligne de Bon Carburant'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    date = fields.Date(related='gauging_id.date', string='Date', store=True)
    name = fields.Selection([('Bon National', 'Bon National'), ('Bon Total', 'Bon Total')], string='Type de Bon', required=True)
    qty = fields.Integer(string='Quantité de Bons')
    unit_value = fields.Float(string='Valeur Unitaire')
    amount = fields.Float(string='Montant Total', compute='_compute_amount', store=True)

    @api.depends('qty', 'unit_value')
    def _compute_amount(self):
        for line in self:
            line.amount = line.qty * line.unit_value

class GaugingCreditLine(models.Model):
    _name = 'gauging.credit.line'
    _description = 'Ligne de Vente à Crédit'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    date = fields.Date(related='gauging_id.date', string='Date', store=True)
    customer_name = fields.Char(string='Nom du Client')
    reference = fields.Char(string='Référence / Fiche')
    amount = fields.Float(string='Montant du Crédit')

class GaugingCheckLine(models.Model):
    _name = 'gauging.check.line'
    _description = 'Ligne de Chèque'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    date = fields.Date(related='gauging_id.date', string='Date', store=True)
    customer_name = fields.Char(string='Nom du Client')
    check_number = fields.Char(string='Numéro du Chèque')
    bank = fields.Char(string='Banque Émettrice')
    amount = fields.Float(string='Montant du Chèque')

class GaugingDisbursement(models.Model):
    _name = 'gauging.disbursement'
    _description = 'Ligne de Sortie de Caisse'
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')
    beneficiary = fields.Char(string='Raison / Bénéficiaire')
    amount = fields.Float(string='Montant de la Dépense')


# =========================================================================
# MODÈLES POUR RAPPORTS CONSOLIDÉS (TABLEAUX DE BORD AM+PM)
# =========================================================================

class GaugingDailyDecompte(models.Model):
    _name = 'gauging.daily.decompte'
    _description = 'Rapport de Décompte Consolidé'

    name = fields.Char(string='Référence', compute='_compute_name')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    supervisor_id = fields.Many2one('res.users', string='Superviseur', default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')], default='draft', string='Statut')

    total_cash = fields.Float(string='Total Cash (Journée)')
    total_carte = fields.Float(string='Total Cartes / TPE (Journée)')
    total_coupons = fields.Float(string='Total Bons (Journée)')
    total_cheque = fields.Float(string='Total Chèques (Journée)')
    total_credit = fields.Float(string='Total Crédits (Journée)')

    tank_1_sold = fields.Float(string='Quantité Super Tank 1', digits=(16, 3))
    tank_2_sold = fields.Float(string='Quantité Super Tank 2', digits=(16, 3))
    tank_3_sold = fields.Float(string='Quantité Diesel Tank 3', digits=(16, 3))
    tank_4_sold = fields.Float(string='Quantité Diesel Tank 4', digits=(16, 3))
    tank_5_sold = fields.Float(string='Quantité Super Tank 5', digits=(16, 3))
    tank_6_sold = fields.Float(string='Quantité Super Tank 6', digits=(16, 3))
    propane_1_sold = fields.Float(string='Quantité Propane Tank 1', digits=(16, 3))
    propane_2_sold = fields.Float(string='Quantité Propane Tank 2', digits=(16, 3))

    @api.depends('date')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Décompte Général du {rec.date}"

    def action_generate(self):
        for rec in self:
            gaugings = self.env['gauging.gauging'].search([('date', '=', rec.date), ('state', '=', 'validated')])
            
            # SECURITÉ AJOUTÉE : Avertit l'utilisateur s'il a oublié de valider la fiche AM/PM
            if not gaugings:
                raise UserError(_("⚠️ ALERTE : Aucun jaugeage 'Validé' n'a été trouvé pour la date du %s. Vous devez d'abord Valider vos fiches de shifts (AM ou PM) avant de générer le Grand Total !") % rec.date)

            rec.total_cash = sum(gaugings.mapped('total_cash_htg'))
            rec.total_carte = sum(gaugings.mapped('total_tpe'))
            rec.total_coupons = sum(gaugings.mapped('coupon_line_ids.amount'))
            rec.total_cheque = sum(gaugings.mapped('check_line_ids.amount'))
            rec.total_credit = sum(gaugings.mapped('credit_line_ids.amount'))

            tanks = self.env['gauging.tank.line'].search([('gauging_id', 'in', gaugings.ids)])
            rec.tank_1_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Super Tank 1').mapped('qty_sold'))
            rec.tank_2_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Super Tank 2').mapped('qty_sold'))
            rec.tank_3_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Diesel Tank 3').mapped('qty_sold'))
            rec.tank_4_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Diesel Tank 4').mapped('qty_sold'))
            rec.tank_5_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Super Tank 5').mapped('qty_sold'))
            rec.tank_6_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Super Tank 6').mapped('qty_sold'))
            rec.propane_1_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Propane Tank 1').mapped('qty_sold'))
            rec.propane_2_sold = sum(tanks.filtered(lambda t: t.tank_name == 'Propane Tank 2').mapped('qty_sold'))

    def action_validate(self):
        self.state = 'validated'

class GaugingDailyInventaire(models.Model):
    _name = 'gauging.daily.inventaire'
    _description = 'Rapport d\'Inventaire Résumé'

    name = fields.Char(string='Référence', compute='_compute_name')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')], default='draft', string='Statut')
    line_ids = fields.One2many('gauging.daily.inventaire.line', 'report_id', string='Lignes d\'Inventaire')

    @api.depends('date')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Inventaire Consolidé du {rec.date}"

    def action_generate(self):
        for rec in self:
            rec.line_ids.unlink()
            gaugings = self.env['gauging.gauging'].search([('date', '=', rec.date), ('state', '=', 'validated')])
            
            if not gaugings:
                raise UserError(_("⚠️ ALERTE : Aucun jaugeage 'Validé' n'a été trouvé pour la date du %s.") % rec.date)

            am_gaugings = gaugings.filtered(lambda g: g.shift == 'am')
            pm_gaugings = gaugings.filtered(lambda g: g.shift == 'pm')

            tanks_list =['Super Tank 1', 'Super Tank 2', 'Diesel Tank 3', 'Diesel Tank 4', 'Super Tank 5', 'Super Tank 6', 'Propane Tank 1', 'Propane Tank 2']
            lines =[]
            for t_name in tanks_list:
                am_line = am_gaugings.tank_line_ids.filtered(lambda l: l.tank_name == t_name) if am_gaugings else False
                pm_line = pm_gaugings.tank_line_ids.filtered(lambda l: l.tank_name == t_name) if pm_gaugings else False
                open_am = am_line[0].opening_qty if am_line else 0.0
                close_pm = pm_line[0].closing_qty if pm_line else 0.0

                lines.append((0, 0, {'tank_name': t_name, 'open_am': open_am, 'close_pm': close_pm}))
            rec.line_ids = lines

    def action_validate(self):
        self.state = 'validated'

class GaugingDailyInventaireLine(models.Model):
    _name = 'gauging.daily.inventaire.line'
    _description = 'Ligne d\'Inventaire Résumé'

    report_id = fields.Many2one('gauging.daily.inventaire', ondelete='cascade')
    tank_name = fields.Char(string='Nom de la Cuve')
    open_am = fields.Float(string='Ouverture Shift AM', digits=(16, 3))
    close_pm = fields.Float(string='Fermeture Shift PM', digits=(16, 3))
    variance = fields.Float(string='Quantité Vendue (Journée)', compute='_compute_variance', digits=(16, 3))

    @api.depends('open_am', 'close_pm')
    def _compute_variance(self):
        for line in self:
            line.variance = line.open_am - line.close_pm