"""
Crypto Payment Integration - Coinbase Commerce
- Accept BTC, ETH, USDC, and other cryptocurrencies
- Real-time payment verification
- Automatic conversion to USD
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from models import Transaction, TransactionItem
from datetime import datetime
import os
import requests
import hmac
import hashlib

crypto_bp = Blueprint('crypto', __name__)

COINBASE_API_KEY = os.getenv('COINBASE_COMMERCE_API_KEY')
COINBASE_WEBHOOK_SECRET = os.getenv('COINBASE_COMMERCE_WEBHOOK_SECRET')


@crypto_bp.route('/create-charge', methods=['POST'])
@jwt_required()
def create_crypto_charge():
    """
    Create Coinbase Commerce charge for crypto payment
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        data = request.json

        # Get transaction details
        amount = float(data.get('amount'))
        description = data.get('description', 'OnyxPOS Transaction')
        transaction_data = data.get('transaction_data', {})

        # Create charge with Coinbase Commerce
        headers = {
            'X-CC-Api-Key': COINBASE_API_KEY,
            'X-CC-Version': '2018-03-22',
            'Content-Type': 'application/json',
        }

        charge_data = {
            'name': description,
            'description': f'Payment for {description}',
            'pricing_type': 'fixed_price',
            'local_price': {
                'amount': str(amount),
                'currency': 'USD'
            },
            'metadata': {
                'tenant_id': tenant_id,
                'user_id': user_id,
                'transaction_data': transaction_data,
            },
            'redirect_url': data.get('redirect_url', 'http://localhost:3000/sales?payment=success'),
            'cancel_url': data.get('cancel_url', 'http://localhost:3000/sales?payment=canceled'),
        }

        response = requests.post(
            'https://api.commerce.coinbase.com/charges',
            json=charge_data,
            headers=headers
        )

        if response.status_code == 201:
            charge = response.json()['data']

            return jsonify({
                'charge_id': charge['id'],
                'hosted_url': charge['hosted_url'],  # URL to send customer to
                'code': charge['code'],
                'pricing': charge['pricing'],
                'addresses': charge['addresses'],  # Crypto addresses for payment
            }), 201
        else:
            return jsonify({
                'error': 'Failed to create charge',
                'details': response.json()
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@crypto_bp.route('/webhook', methods=['POST'])
def coinbase_webhook():
    """
    Handle Coinbase Commerce webhooks
    """
    payload = request.data
    sig_header = request.headers.get('X-CC-Webhook-Signature')

    # Verify webhook signature
    try:
        computed_sig = hmac.new(
            COINBASE_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(sig_header, computed_sig):
            return jsonify({'error': 'Invalid signature'}), 400
    except Exception:
        return jsonify({'error': 'Signature verification failed'}), 400

    # Process event
    event = request.json
    event_type = event.get('event', {}).get('type')

    if event_type == 'charge:confirmed':
        handle_charge_confirmed(event['event']['data'])

    elif event_type == 'charge:failed':
        handle_charge_failed(event['event']['data'])

    elif event_type == 'charge:pending':
        handle_charge_pending(event['event']['data'])

    return jsonify({'status': 'success'}), 200


def handle_charge_confirmed(charge_data):
    """Handle confirmed crypto payment"""
    from database import Session
    db = Session()

    try:
        metadata = charge_data.get('metadata', {})
        tenant_id = metadata.get('tenant_id')
        user_id = metadata.get('user_id')
        transaction_data = metadata.get('transaction_data', {})

        # Get payment details
        payment = charge_data['payments'][0]  # First confirmed payment

        # Create transaction record
        transaction = Transaction(
            tenant_id=tenant_id,
            transaction_number=f"CRYPTO-{charge_data['code']}",
            transaction_date=datetime.utcnow(),
            subtotal=float(charge_data['pricing']['local']['amount']),
            tax_amount=0,  # Already included in total
            total_amount=float(charge_data['pricing']['local']['amount']),
            payment_method='crypto',
            payment_status='completed',
            cashier_id=user_id,

            # Crypto-specific fields
            crypto_currency=payment['value']['crypto']['currency'],
            crypto_amount=float(payment['value']['crypto']['amount']),
            crypto_tx_hash=payment['transaction_id'],
            crypto_exchange_rate=float(payment['value']['local']['amount']) / float(payment['value']['crypto']['amount'])
        )

        db.add(transaction)
        db.commit()

        print(f"✅ Crypto payment confirmed: {charge_data['code']}")

        # TODO: Send email confirmation

    except Exception as e:
        print(f"❌ Error processing crypto payment: {e}")
        db.rollback()
    finally:
        db.close()


def handle_charge_failed(charge_data):
    """Handle failed crypto payment"""
    print(f"❌ Crypto payment failed: {charge_data['code']}")
    # TODO: Notify user


def handle_charge_pending(charge_data):
    """Handle pending crypto payment"""
    print(f"⏳ Crypto payment pending: {charge_data['code']}")
    # TODO: Update transaction status


@crypto_bp.route('/supported-currencies', methods=['GET'])
def get_supported_currencies():
    """
    Get list of supported cryptocurrencies
    """
    return jsonify({
        'currencies': [
            {
                'code': 'BTC',
                'name': 'Bitcoin',
                'type': 'crypto'
            },
            {
                'code': 'ETH',
                'name': 'Ethereum',
                'type': 'crypto'
            },
            {
                'code': 'USDC',
                'name': 'USD Coin',
                'type': 'stablecoin'
            },
            {
                'code': 'DAI',
                'name': 'Dai',
                'type': 'stablecoin'
            },
            {
                'code': 'LTC',
                'name': 'Litecoin',
                'type': 'crypto'
            },
            {
                'code': 'BCH',
                'name': 'Bitcoin Cash',
                'type': 'crypto'
            },
        ]
    }), 200


@crypto_bp.route('/exchange-rates', methods=['GET'])
def get_exchange_rates():
    """
    Get current crypto exchange rates
    """
    try:
        # Get rates from Coinbase
        response = requests.get('https://api.coinbase.com/v2/exchange-rates?currency=USD')

        if response.status_code == 200:
            rates = response.json()['data']['rates']

            # Return rates for our supported currencies
            return jsonify({
                'BTC': float(rates.get('BTC', 0)),
                'ETH': float(rates.get('ETH', 0)),
                'USDC': float(rates.get('USDC', 1.0)),
                'DAI': float(rates.get('DAI', 1.0)),
                'LTC': float(rates.get('LTC', 0)),
                'BCH': float(rates.get('BCH', 0)),
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({'error': 'Failed to fetch rates'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
