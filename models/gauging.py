from odoo import models, fields, api, _ 

class Gauging(models.Model):  # Définition du modèle principal
    _name = 'gauging.gauging'  # Nom technique strict
    _description = 'Fiche de Gauging'  # Description du modèle
    _order = 'date desc'  # Tri par date décroissante

    # --- Section Création ---
    name = fields.Char(string='ID', required=True, copy=False, readonly=True, default=lambda self: _('Nouveau'))  # ID auto
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)  # Date actuelle auto
    user_id = fields.Many2one('res.users', string='User connecté', default=lambda self: self.env.user, readonly=True)  # Superviseur
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')], default='draft', string="Statut")  # État de validation

    # --- Section Relations One2many ---
    tank_line_ids = fields.One2many('gauging.tank.line', 'gauging_id', string='Réservoirs')  # Lien jaugeage réservoirs
    pump_line_ids = fields.One2many('gauging.pump.line', 'gauging_id', string='Lignes Pompes')  # Lien ventes pompes
    check_line_ids = fields.One2many('gauging.check.line', 'gauging_id', string='Chèques')  # Lien liste chèques
    credit_line_ids = fields.One2many('gauging.credit.line', 'gauging_id', string='Fiches de Crédit')  # Lien fiches crédit

    # --- Section Décompte Financier ---
    cash_HTG = fields.Float(string='cash_HTG')  # Espèces en HTG
    cash_USD = fields.Float(string='cash_USD')  # Espèces en USD
    card_HTG = fields.Float(string='card_HTG')  # Carte en HTG
    card_USD = fields.Float(string='card_USD')  # Carte en USD
    coupon_1000_HTG = fields.Integer(string='coupon_1000_HTG')  # Nombre coupons 1000
    coupon_500_HTG = fields.Integer(string='coupon_500_HTG')  # Nombre coupons 500

    # --- Section Calculs Stockés ---
    expected_amount = fields.Float(string='expected_amount', compute='_compute_totals', store=True)  # Total théorique ventes
    counted_amount_total = fields.Float(string='counted_amount_total', compute='_compute_totals', store=True)  # Total réel compté
    difference = fields.Float(string='difference', compute='_compute_totals', store=True, readonly=True)  # Écart (Readonly)

    @api.depends('pump_line_ids.amount_sold', 'cash_HTG', 'cash_USD', 'card_HTG', 'card_USD', 'coupon_1000_HTG', 'coupon_500_HTG', 'check_line_ids.amount', 'credit_line_ids.amount')
    def _compute_totals(self):  # Calcul des totaux et de l'écart
        for rec in self:  # Parcours des fiches
            rec.expected_amount = sum(rec.pump_line_ids.mapped('amount_sold'))  # Somme des montants vendus aux pompes
            total_cash = rec.cash_HTG + rec.cash_USD  # Somme des espèces
            total_cards = rec.card_HTG + rec.card_USD  # Somme des cartes
            total_coupons = (rec.coupon_1000_HTG * 1000) + (rec.coupon_500_HTG * 500)  # Somme des coupons
            total_checks = sum(rec.check_line_ids.mapped('amount'))  # Somme des chèques
            total_credits = sum(rec.credit_line_ids.mapped('amount'))  # Somme des fiches crédit
            rec.counted_amount_total = total_cash + total_cards + total_coupons + total_checks + total_credits  # Total général compté
            rec.difference = rec.counted_amount_total - rec.expected_amount  # Calcul final de l'écart

    @api.model
    def create(self, vals):  # Surcharge de la création pour la séquence
        if vals.get('name', _('Nouveau')) == _('Nouveau'):  # Vérifie si c'est une nouvelle fiche
            vals['name'] = self.env['ir.sequence'].next_by_code('gauging.gauging') or _('Nouveau')  # Génère l'ID unique
        return super(Gauging, self).create(vals)  # Appelle la création standard

    def action_validate(self):  # Méthode de validation
        self.write({'state': 'validated'})  # Change le statut pour verrouiller la fiche

class GaugingTankLine(models.Model):  # Modèle détail réservoirs
    _name = 'gauging.tank.line'  # Nom technique
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')  # Lien vers parent
    tank_name = fields.Char(string='Réservoir')  # Nom du réservoir
    start_inches = fields.Float(string='start_inches')  # Pouces début
    end_inches = fields.Float(string='end_inches')  # Pouces fin
    start_gallons = fields.Float(string='start_gallons')  # Gallons début
    end_gallons = fields.Float(string='end_gallons')  # Gallons fin
    variation_gallons = fields.Float(string='variation_gallons', compute='_compute_variation', store=True)  # Calcul variation

    @api.depends('start_gallons', 'end_gallons')
    def _compute_variation(self):  # Calcul de la variation volume
        for line in self:  # Pour chaque ligne
            line.variation_gallons = line.end_gallons - line.start_gallons  # Soustraction gallons fin - début

class GaugingPumpLine(models.Model):  # Modèle détail pompes
    _name = 'gauging.pump.line'  # Nom technique
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')  # Lien vers parent
    product_id = fields.Many2one('product.template', string='product_id')  # Article carburant
    pump_id = fields.Char(string='pump_id')  # ID de la pompe/face
    employee_id = fields.Many2one('hr.employee', string='employee_id')  # Employé responsable
    start_counter = fields.Float(string='start_counter')  # Compteur début
    end_counter = fields.Float(string='end_counter')  # Compteur fin
    unit_price = fields.Float(string='unit_price', related='product_id.list_price', store=True)  # Prix unitaire auto
    quantity_sold = fields.Float(string='quantity_sold', compute='_compute_sold', store=True)  # Qté vendue calculée
    amount_sold = fields.Float(string='amount_sold', compute='_compute_sold', store=True)  # Montant vendu calculé

    @api.depends('start_counter', 'end_counter', 'unit_price')
    def _compute_sold(self):  # Calcul des ventes par pompe
        for line in self:  # Pour chaque pompe
            line.quantity_sold = line.end_counter - line.start_counter  # Différence compteurs
            line.amount_sold = line.quantity_sold * line.unit_price  # Multiplication par prix unitaire

class GaugingCheckLine(models.Model):  # Modèle custom chèques
    _name = 'gauging.check.line'  # Nom technique
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')  # Lien vers parent
    amount = fields.Float(string='Montant')  # Valeur du chèque

class GaugingCreditLine(models.Model):  # Modèle custom crédits
    _name = 'gauging.credit.line'  # Nom technique
    gauging_id = fields.Many2one('gauging.gauging', ondelete='cascade')  # Lien vers parent
    amount = fields.Float(string='Montant')  # Valeur du bon de crédit