# Telegram Content Bot

A Telegram bot for delivering educational content (videos and books) with subscription-based access control.

## Features

- User registration and authentication
- Content delivery system (videos and books)
- Subscription management with multiple payment options
- Admin panel for content management
- User interaction tracking and analytics

## Payment Options

The bot supports multiple payment methods:

1. **Telegram Payments** - Primary payment method
2. **Stripe** - Future enhancement
3. **PayPal** - Future enhancement
4. **Chapa** - Ethiopian payment gateway for mobile money and bank transfers

### Chapa Integration

Chapa is now available as a payment option, particularly suitable for Ethiopian users as it supports mobile money and bank transfers.

To use Chapa:
1. Users can select Chapa as their payment method when subscribing
2. They will be redirected to Chapa's payment page
3. After successful payment, their subscription will be activated automatically

Configuration:
- Add `CHAPA_SECRET_KEY` and `CHAPA_PUBLIC_KEY` to your environment variables
- Set up webhook URL in Chapa dashboard to point to your server

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.example`)
4. Configure database
5. Run the bot: `python bot.py`

## Configuration

See `.env.example` for required environment variables.

## Project Structure

See `project_structure.md` for detailed file organization.

## Documentation

- `database_schema.md` - Database design
- `user_auth_subscription.md` - User authentication and subscription management
- `payment_systems.md` - Payment systems integration
- `admin_panel_design.md` - Admin panel design and functionality
- `content_delivery_system.md` - Content delivery system implementation