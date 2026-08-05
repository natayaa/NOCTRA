# migrations/versions/xxxx_update_inquiry_models.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade():
    # 1. Tambahkan project_id ke tb_customer_inquiry
    op.add_column('tb_customer_inquiry',
                  sa.Column('project_id', UUID, nullable=True,
                            comment='ID project yang terkonversi')
                  )
    op.create_index('idx_inquiry_project_id',
                    'tb_customer_inquiry', ['project_id'])

    # 2. Tambahkan is_deleted dan deleted_at (soft delete)
    op.add_column('tb_customer_inquiry',
                  sa.Column('is_deleted', sa.Boolean, nullable=False,
                            server_default='false', comment='Soft delete flag')
                  )
    op.add_column('tb_customer_inquiry',
                  sa.Column('deleted_at', sa.DateTime(timezone=True),
                            nullable=True, comment='Waktu delete')
                  )
    op.create_index('idx_inquiry_deleted',
                    'tb_customer_inquiry', ['is_deleted'])

    # 3. Tambahkan comment di semua kolom (optional)
    # ... tambahkan komentar untuk dokumentasi

    # 4. Buat tabel InquiryPayment jika belum ada
    op.create_table('tb_inquiry_payments',
                    sa.Column('id', UUID, primary_key=True,
                              default=sa.text('gen_random_uuid()')),
                    sa.Column('inquiry_id', UUID, sa.ForeignKey(
                        'tb_customer_inquiry.id', ondelete='CASCADE'), nullable=False),
                    sa.Column('payment_type', sa.String(50), nullable=False),
                    sa.Column('amount', sa.Numeric(12, 2), nullable=False),
                    sa.Column('status', sa.String(50), nullable=False,
                              server_default='pending'),
                    sa.Column('payment_method', sa.String(50), nullable=True),
                    sa.Column('paid_at', sa.DateTime(
                        timezone=True), nullable=True),
                    sa.Column('reference', sa.String(100), nullable=True),
                    sa.Column('notes', sa.Text, nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.func.now()),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.func.now()),
                    # Constraints
                    sa.CheckConstraint(
                        "payment_type IN ('deposit', 'payment', 'refund', 'installment')", name='ck_payment_type'),
                    sa.CheckConstraint(
                        "status IN ('pending', 'completed', 'failed', 'cancelled', 'refunded', 'partial')", name='ck_payment_status'),
                    )
    op.create_index('idx_payment_inquiry_status',
                    'tb_inquiry_payments', ['inquiry_id', 'status'])
    op.create_index('idx_payment_paid_at', 'tb_inquiry_payments', ['paid_at'])

    # 5. Buat tabel InquiryInvoice jika belum ada
    op.create_table('tb_inquiry_invoices',
                    sa.Column('id', UUID, primary_key=True,
                              default=sa.text('gen_random_uuid()')),
                    sa.Column('inquiry_id', UUID, sa.ForeignKey(
                        'tb_customer_inquiry.id', ondelete='CASCADE'), nullable=False),
                    sa.Column('invoice_number', sa.String(
                        50), nullable=False, unique=True),
                    sa.Column('amount', sa.Numeric(12, 2), nullable=False),
                    sa.Column('status', sa.String(50),
                              nullable=False, server_default='draft'),
                    sa.Column('issued_at', sa.DateTime(
                        timezone=True), nullable=True),
                    sa.Column('due_date', sa.DateTime(
                        timezone=True), nullable=True),
                    sa.Column('paid_at', sa.DateTime(
                        timezone=True), nullable=True),
                    sa.Column('file_path', sa.String(500), nullable=True),
                    sa.Column('notes', sa.Text, nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.func.now()),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.func.now()),
                    # Constraints
                    sa.CheckConstraint(
                        "status IN ('draft', 'sent', 'viewed', 'partial', 'paid', 'overdue', 'cancelled', 'refunded')", name='ck_invoice_status'),
                    )
    op.create_index('idx_invoice_inquiry_status',
                    'tb_inquiry_invoices', ['inquiry_id', 'status'])
    op.create_index('idx_invoice_due_date',
                    'tb_inquiry_invoices', ['due_date'])
    op.create_index('idx_invoice_number',
                    'tb_inquiry_invoices', ['invoice_number'])


def downgrade():
    op.drop_table('tb_inquiry_invoices')
    op.drop_table('tb_inquiry_payments')
    op.drop_index('idx_inquiry_deleted', 'tb_customer_inquiry')
    op.drop_column('tb_customer_inquiry', 'deleted_at')
    op.drop_column('tb_customer_inquiry', 'is_deleted')
    op.drop_index('idx_inquiry_project_id', 'tb_customer_inquiry')
    op.drop_column('tb_customer_inquiry', 'project_id')
