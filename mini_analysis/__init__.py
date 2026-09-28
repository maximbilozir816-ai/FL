"""
Free "Ratio Analysis" feature.

Everything related to the free mini-analysis (state, texts, keyboards,
DB access, document generation, handlers, admin command) lives in this
package. It intentionally does NOT import from `database.repository`
(UserRepository) or touch `balance` / `total_purchased` — those remain
100% owned by the payment system.
"""
