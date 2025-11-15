from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.utils import timezone


class Student(models.Model):
    firstname = models.CharField(max_length=20)
    lastname = models.CharField(max_length=20)
    idnumber = models.CharField(max_length=20, unique=True)
    phonenumber = models.CharField(max_length=15)  # store as string to keep leading zeros

    def __str__(self):
        return f"{self.firstname} {self.lastname} {self.idnumber}"


class Payment(models.Model):
    STATUS_NOT_REQUESTED = "not_requested"
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"

    PAYMENT_STATUS_CHOICES = [
        (STATUS_NOT_REQUESTED, "Not requested"),
        (STATUS_PENDING, "Pending confirmation"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    mpesa_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=STATUS_NOT_REQUESTED,
    )
    mpesa_checkout_request_id = models.CharField(max_length=64, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=32, blank=True, null=True)
    mpesa_phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.student.firstname} - {self.amount}"


class UsageSession(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("not_requested", "Not requested"),
        ("awaiting_payment", "Awaiting payment"),
        ("pending", "Pending confirmation"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]
    BILL_RATE_PER_HOUR = Decimal("100.00")

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    amount_charged = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="not_requested")
    mpesa_checkout_request_id = models.CharField(max_length=64, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=32, blank=True, null=True)
    mpesa_phone_number = models.CharField(max_length=15, blank=True, null=True)

    def duration_in_hours(self):
        """
        Pretty HH:MM:SS string used for the dashboard.
        """
        end = self.end_time or timezone.now()
        duration = end - self.start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def billable_amount(self):
        """
        Decimal-friendly amount used for billing / STK pushes.
        """
        end = self.end_time or timezone.now()
        duration_seconds = Decimal((end - self.start_time).total_seconds())
        hours = duration_seconds / Decimal("3600")
        amount = (hours * self.BILL_RATE_PER_HOUR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return amount

    def total_amount(self):
        return self.billable_amount()

    def __str__(self):
        return f"{self.student.firstname} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"