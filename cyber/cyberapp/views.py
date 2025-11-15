import json
import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_daraja.mpesa.core import MpesaClient
from django_daraja.mpesa.exceptions import (
    IllegalPhoneNumberException,
    MpesaConnectionError,
    MpesaInvalidParameterException,
)
from django_daraja.mpesa.utils import format_phone_number as daraja_format_phone_number

from .forms import StudentForm, PaymentForm
from .models import Student, Payment, UsageSession


# Create your views here.

logger = logging.getLogger(__name__)


TOTAL_MACHINES = 30


def _prepare_phone_number(raw_phone: str) -> str:
    """
    Normalize phone numbers captured as integers/strings into a format that
    django-daraja can validate (e.g. 07xx..., 7xx..., +2547xx...).
    """
    if raw_phone is None:
        return ""

    phone = str(raw_phone).strip()
    phone = phone.replace(" ", "").replace("-", "")

    if phone.startswith("+"):
        phone = phone[1:]

    if phone.isdigit() and len(phone) == 9 and phone.startswith("7"):
        phone = f"0{phone}"

    return phone


def _resolve_callback_url(request):
    callback_url = getattr(settings, "MPESA_CALLBACK_URL", "")
    if not callback_url or "yourdomain.com" in callback_url:
        callback_url = request.build_absolute_uri(reverse("mpesa_callback"))
    return callback_url


def _send_stk_request(*, phone_input, amount_decimal, account_reference, transaction_desc, request):
    phone_input = _prepare_phone_number(phone_input)
    if not phone_input:
        raise ValueError("Phone number is required for STK push.")

    try:
        formatted_phone = daraja_format_phone_number(phone_input)
    except IllegalPhoneNumberException as exc:
        raise ValueError(str(exc)) from exc

    amount_decimal = Decimal(amount_decimal)
    if amount_decimal <= 0:
        raise ValueError("Amount must be greater than zero.")

    amount_integer = int(amount_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    callback_url = _resolve_callback_url(request)

    client = MpesaClient()
    try:
        response = client.stk_push(
            phone_number=formatted_phone,
            amount=amount_integer,
            account_reference=account_reference[:12],
            transaction_desc=transaction_desc[:13],
            callback_url=callback_url,
        )
    except (MpesaConnectionError, MpesaInvalidParameterException) as exc:
        raise RuntimeError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Unexpected STK error")
        raise RuntimeError(f"Could not initiate STK push: {exc}") from exc

    return response, formatted_phone


def _format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@login_required
def home(request):
    """
    Feed every dashboard widget with realtime, financial, and roster data.
    """
    now = timezone.now()

    students = list(
        Student.objects.prefetch_related("usagesession_set")
        .order_by("firstname", "lastname")
    )

    active_sessions = list(
        UsageSession.objects.filter(is_active=True, end_time__isnull=True)
        .select_related("student")
        .order_by("start_time")
    )
    active_sessions_count = len(active_sessions)

    utilization_rate = 0
    if TOTAL_MACHINES:
        utilization_rate = min(
            100,
            round((active_sessions_count / TOTAL_MACHINES) * 100),
        )

    total_students = Student.objects.count()
    sessions_started_today = UsageSession.objects.filter(
        start_time__date=now.date()
    ).count()

    recent_completed_sessions = list(
        UsageSession.objects.filter(end_time__isnull=False)
        .order_by("-end_time")[:10]
    )
    avg_session_length = "00:00:00"
    if recent_completed_sessions:
        total_seconds = sum(
            (session.end_time - session.start_time).total_seconds()
            for session in recent_completed_sessions
        )
        avg_session_length = _format_duration(
            int(total_seconds / len(recent_completed_sessions))
        )

    revenue_today = (
        Payment.objects.filter(date=now.date())
        .aggregate(total=Sum("amount"))
        .get("total")
    ) or Decimal("0.00")

    outstanding_balance = (
        Payment.objects.filter(balance__gt=0)
        .aggregate(total=Sum("balance"))
        .get("total")
    ) or Decimal("0.00")

    recent_payments = list(
        Payment.objects.select_related("student")
        .order_by("-date", "-id")[:6]
    )

    for student in students:
        sessions = student.usagesession_set.all()
        active_session = next(
            (s for s in sessions if s.is_active and not s.end_time), None
        )
        if active_session:
            student.active_start_time = active_session.start_time
            student.has_active_session = True
            student.duration_in_hours = active_session.duration_in_hours()
        else:
            student.active_start_time = None
            student.has_active_session = False
            student.duration_in_hours = "—"

    context = {
        "students": students,
        "now": now,
        "active_sessions": active_sessions,
        "active_sessions_count": active_sessions_count,
        "utilization_rate": utilization_rate,
        "total_students": total_students,
        "sessions_started_today": sessions_started_today,
        "avg_session_length": avg_session_length,
        "revenue_today": revenue_today,
        "outstanding_balance": outstanding_balance,
        "recent_payments": recent_payments,
    }
    return render(request, "home.html", context)

@login_required
def students_list(request):
    students = Student.objects.all()
    return render(request, 'students_list.html', {'students': students})

@login_required
def student_detail(request, idnumber):
    student = Student.objects.get(idnumber=idnumber)
    payments = student.payments.all()
    return render(request, 'student_detail.html', {'student': student, 'payments': payments})

def student_payments(request, idnumber):
    student = Student.objects.get(idnumber=idnumber)
    payments = student.payments.all()
    return render(request, 'student_payments.html', {'student': student, 'payments': payments})

@login_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            idnumber = form.cleaned_data['idnumber']
            if not Student.objects.filter(idnumber=idnumber).exists():
                form.save()
                messages.success(request, 'Student added successfully.')
                return redirect('students_list')
            else:
                form.add_error('idnumber', 'Student with this ID number already exists.')
    else:
        form = StudentForm()
    return render(request, 'add_student.html', {'form': form})

#delete student function
@login_required
def delete_student(request, idnumber):
    student = get_object_or_404(Student, idnumber=idnumber)
    student_name = f"{student.firstname} {student.lastname}"
    student.delete()
    messages.success(request, f'Student {student_name} deleted successfully.')
    return redirect('home')

def payment_list(request):
    payments = Payment.objects.select_related('student').all().order_by('-date')
    return render(request, 'payment_list.html', {'payments': payments})

def delete_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    payment_name = f"{payment.student.firstname} {payment.student.lastname} - {payment.amount} on {payment.date}"
    payment.delete()
    messages.success(request, f'Payment {payment_name} deleted successfully.')
    return redirect('payment_list')

@login_required
def add_payment(request):
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            phone_override = form.cleaned_data.get("phone_number")
            phone_source = phone_override or payment.student.phonenumber

            try:
                response, formatted_phone = _send_stk_request(
                    phone_input=phone_source,
                    amount_decimal=payment.amount,
                    account_reference=f"Pay-{payment.student.idnumber}",
                    transaction_desc=f"Payment {payment.date:%m%d}",
                    request=request,
                )
            except ValueError as exc:
                form.add_error("phone_number", str(exc))
            except RuntimeError as exc:
                form.add_error(None, str(exc))
            else:
                if response.get("ResponseCode") == "0":
                    payment.mpesa_status = Payment.STATUS_PENDING
                    payment.mpesa_checkout_request_id = response.get("CheckoutRequestID")
                    payment.mpesa_phone_number = formatted_phone
                    payment.save()
                    messages.success(
                        request,
                        "Payment saved and STK push sent. Ask the customer to enter their PIN.",
                    )
                    return redirect("payment_list")
                else:
                    form.add_error(
                        None,
                        response.get("errorMessage", "STK push rejected by Safaricom."),
                    )
    else:
        form = PaymentForm()
    return render(request, "add_payment.html", {"form": form})

# update student function
@login_required
def update_student(request, idnumber):
    student = get_object_or_404(Student, idnumber=idnumber)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully.')
            return redirect('home')
    else:
        form = StudentForm(instance=student)
    return render(request, 'update_student.html', {'form': form})


@login_required
def start_session(request, idnumber):
    student = get_object_or_404(Student, idnumber=idnumber)

    # End any existing active sessions for this student
    UsageSession.objects.filter(
        student=student,
        is_active=True,
        end_time__isnull=True
        ).update(
        is_active=False,
        end_time=timezone.now()
    )

    # Start a new session (always triggered when link is clicked)
    UsageSession.objects.create(
        student=student,
        start_time=timezone.now(),
        is_active=True)

    # Add a small success message
    messages.success(request, f"Session started for {student.firstname} {student.lastname}.")

    # Redirect back to homepage
    return redirect('home')


# Update to views.py - end_session view
@login_required
def end_session(request, idnumber):
    student = get_object_or_404(Student, idnumber=idnumber)
    session = UsageSession.objects.filter(
        student=student,
        is_active=True,
        end_time__isnull=True
    ).first()
    
    if session:
        if request.method == 'POST':
            session.end_time = timezone.now()
            session.is_active = False
            amount_due = session.total_amount()
            session.amount_charged = amount_due
            session.save()
            
            # Add message only for non-AJAX (AJAX uses toast)
            if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                messages.success(request, f"Session ended for {student.firstname} {student.lastname}. Amount due: {amount_due} KSH.")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # AJAX
                return JsonResponse({'status': 'success', 'amount': str(amount_due)})  # str() fixes serialization
            else:
                next_page = request.GET.get('next', 'active_sessions')
                return redirect(next_page)
        else:
            # GET: Redirect to avoid direct access
            return redirect('active_sessions')
    else:
        error_msg = "No active session found."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': error_msg})
        messages.error(request, error_msg)
        return redirect('active_sessions')

def active_sessions(request):
    sessions = UsageSession.objects.filter(
        is_active=True,
        end_time__isnull=True
    ).select_related('student')
    context = {
        'sessions': sessions,
        'now': timezone.now(),  # For header date
    }
    return render(request, 'active_sessions.html', context)

@login_required
def summary_session(request):
    """
    Display a quick summary of the most recent session (completed if available,
    otherwise the latest active one) so the "Session summary" action on the
    dashboard always has a destination.
    """
    latest_session = (
        UsageSession.objects.select_related("student")
        .order_by("-end_time", "-start_time")
        .first()
    )

    context = {
        "session": latest_session,
    }
    return render(request, "summary_session.html", context)


@login_required
@require_http_methods(["POST"])
def send_stk(request, session_id):
    session = get_object_or_404(UsageSession, pk=session_id)

    if session.is_active or session.end_time is None:
        return JsonResponse(
            {'success': False, 'message': 'Please end the session before sending an STK push.'},
            status=400
        )

    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)
    else:
        payload = request.POST

    phone_input = (payload.get('phone_number') or "").strip()
    if not phone_input:
        phone_input = str(session.student.phonenumber or "").strip()

    amount = session.amount_charged or session.total_amount()

    try:
        response, formatted_phone = _send_stk_request(
            phone_input=phone_input,
            amount_decimal=amount,
            account_reference=f"Session-{session.id}-{session.student.idnumber}",
            transaction_desc=f"Session {session.id}",
            request=request,
        )
    except ValueError as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)
    except RuntimeError as exc:
        logger.exception("STK push error for session %s", session.id)
        return JsonResponse({'success': False, 'message': str(exc)}, status=502)

    if response.get('ResponseCode') == '0':
        session.payment_status = 'pending'
        session.mpesa_checkout_request_id = response.get('CheckoutRequestID')
        session.mpesa_phone_number = formatted_phone
        session.save(update_fields=[
            'payment_status',
            'mpesa_checkout_request_id',
            'mpesa_phone_number',
            'amount_charged'
        ])
        return JsonResponse({
            'success': True,
            'message': 'STK push sent. Ask the customer to check their phone.',
            'checkout_request_id': session.mpesa_checkout_request_id
        })

    logger.warning("STK push rejected for session %s: %s", session.id, response)
    return JsonResponse({
        'success': False,
        'message': response.get('errorMessage', 'STK push rejected by Safaricom.')
    }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """
    Endpoint Safaricom hits with the result of an STK push. Must be publicly reachable.
    """
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON'}, status=400)

    callback = body.get('Body', {}).get('stkCallback', {})
    checkout_request_id = callback.get('CheckoutRequestID')
    result_code = callback.get('ResultCode')

    session = UsageSession.objects.filter(mpesa_checkout_request_id=checkout_request_id).first()
    payment = None
    if not session:
        payment = Payment.objects.filter(mpesa_checkout_request_id=checkout_request_id).first()

    target = session or payment
    if not target:
        logger.warning("Received callback for unknown CheckoutRequestID %s", checkout_request_id)
    else:
        if result_code == 0:
            metadata = callback.get('CallbackMetadata', {}).get('Item', [])
            metadata_map = {item.get('Name'): item.get('Value') for item in metadata if item.get('Name')}

            amount_value = metadata_map.get('Amount')
            receipt_number = metadata_map.get('MpesaReceiptNumber')
            phone_number = metadata_map.get('PhoneNumber')

            if session:
                session.payment_status = 'paid'
                session.mpesa_receipt_number = receipt_number
                if phone_number:
                    session.mpesa_phone_number = str(phone_number)
                if amount_value is not None:
                    try:
                        session.amount_charged = Decimal(str(amount_value))
                    except Exception:
                        pass
                session.save(update_fields=[
                    'payment_status',
                    'mpesa_receipt_number',
                    'mpesa_phone_number',
                    'amount_charged'
                ])
            else:
                payment.mpesa_status = Payment.STATUS_PAID
                payment.mpesa_receipt_number = receipt_number
                if phone_number:
                    payment.mpesa_phone_number = str(phone_number)
                payment.save(update_fields=[
                    'mpesa_status',
                    'mpesa_receipt_number',
                    'mpesa_phone_number',
                ])
        else:
            result_desc = callback.get('ResultDesc', 'Payment failed')
            if session:
                session.payment_status = 'failed'
                session.save(update_fields=['payment_status'])
            if payment:
                payment.mpesa_status = Payment.STATUS_FAILED
                payment.save(update_fields=['mpesa_status'])
            logger.info("STK payment failed for checkout %s: %s", checkout_request_id, result_desc)

    return JsonResponse({
        'ResultCode': 0,
        'ResultDesc': 'Accepted'
    })

# login function view
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password.'})

    return render(request, 'login.html')

# logout function view
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_view(request):
    return render(request, 'profile.html')

# @csrf_exempt
# @require_http_methods(["POST"])
# def mpesa_callback(request):
#     """
#     Endpoint to handle M-Pesa STK Push callbacks.
#     M-Pesa POSTs JSON here after user enters PIN (success/fail).
#     Returns {'ResultCode': 0, 'ResultDesc': 'Accepted'} to acknowledge.
#     """
#     try:
#         # Parse the incoming JSON body from M-Pesa
#         body = json.loads(request.body)
#         callback_data = body.get('Body', {}).get('stkCallback', {})

#         # Extract key fields
#         checkout_request_id = callback_data.get('CheckoutRequestID')
#         result_code = callback_data.get('ResultCode')

#         if result_code == 0:  # Payment successful
#             # Parse metadata for details
#             metadata = callback_data.get('CallbackMetadata', {}).get('Item', [])
#             amount = next((item['Value'] for item in metadata if item['Name'] == 'Amount'), None)
#             receipt_number = next((item['Value'] for item in metadata if item['Name'] == 'MpesaReceiptNumber'), None)
#             phone_number = next((item['Value'] for item in metadata if item['Name'] == 'PhoneNumber'), None)
#             transaction_time = next((item['Value'] for item in metadata if item['Name'] == 'TransactionCompletedTime'), None)

#             # TODO: Update your database here
#             # Example: Find session by checkout_request_id (store it during STK initiation)
#             # from .models import Session
#             # session = Session.objects.get(checkout_request_id=checkout_request_id)
#             # session.payment_status = 'paid'
#             # session.mpesa_receipt = receipt_number
#             # session.amount_paid = amount
#             # session.save()

#             # Log or notify (e.g., send email/SMS)
#             print(f"Payment success: {amount} KSH from {phone_number}, Receipt: {receipt_number}, Time: {transaction_time}")

#         else:  # Payment failed (e.g., cancelled by user)
#             result_desc = callback_data.get('ResultDesc', 'Unknown failure')
            
#             # TODO: Update DB to 'failed'
#             # session = Session.objects.get(checkout_request_id=checkout_request_id)
#             # session.payment_status = 'failed'
#             # session.save()

#             print(f"Payment failed for {checkout_request_id}: {result_desc}")

#         # Always acknowledge to M-Pesa (they require this format)
#         return JsonResponse({
#             'ResultCode': 0,
#             'ResultDesc': 'Accepted'
#         })

#     except json.JSONDecodeError:
#         # Invalid JSON from M-Pesa (rare)
#         return JsonResponse({
#             'ResultCode': 1,
#             'ResultDesc': 'Invalid JSON'
#         }, status=400)

#     except Exception as e:
#         # Catch-all for errors
#         print(f"Callback error: {e}")
#         return JsonResponse({
#             'ResultCode': 1,
#             'ResultDesc': 'Processing failed'
#         }, status=500)

# @login_required
# @require_http_methods(["POST"])
# def sendSTK(request):
#     session_id = request.POST.get('session_id')
#     phone_input = request.POST.get('phone_number')
#     if not session_id:
#         return JsonResponse({'error': 'Session ID required'}, status=400)

#     try:
#         session = UsageSession.objects.get(id=session_id)
#         student = session.student  # Assuming Session has a student foreign key
#         phone = phone_input if phone_input else student.phonenumber# Assume field exists (e.g., '0712345678')
        
#         if not phone:
#             return JsonResponse({'error': 'Phone number required'}, status=400)

#         # Format phone to international: 25471xxxxxxxx
#         if phone.startswith('0'):
#             phone = '254' + phone[1:]
#         elif phone.startswith('7'):
#             phone = '2547' + phone[1:]
#         # Validate: 12 digits starting with 2547
#         if len(phone) != 12 or not phone.startswith('2547'):
#             return JsonResponse({'error': 'Invalid phone format'}, status=400)

#         # Placeholder amount; replace with your logic (e.g., based on session duration)
#         amount = Decimal('1000.00')
        
#         account_reference = f'Session-{session.id}-{student.idnumber}'  # Assuming idnumber field
#         transaction_desc = f'Payment for session {session.id} on {session.start_time.date()}'
#         callback_url = request.build_absolute_uri('/mpesa/callback/')  # Full public HTTPS URL

#         cl = MpesaClient()
#         response = cl.stk_push(
#             phone_number=phone,
#             amount=str(amount),  # Must be string for API
#             account_reference=account_reference,
#             transaction_desc=transaction_desc,
#             callback_url=callback_url
#         )

#         if response.get('ResponseCode') == '0':
#             # Update session (add fields like payment_status, checkout_request_id to your model)
#             session.payment_status = 'pending'
#             session.checkout_request_id = response.get('CheckoutRequestID')
#             session.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': 'STK push sent! Check phone for prompt.',
#                 'checkout_request_id': response.get('CheckoutRequestID')
#             })
#         else:
#             return JsonResponse({
#                 'success': False,
#                 'message': response.get('errorMessage', 'STK push failed')
#             }, status=400)

#     except UsageSession.DoesNotExist:
#         return JsonResponse({'error': 'Session not found'}, status=404)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
#     except Exception as e:
#         return JsonResponse({'error': 'Internal server error'}, status=500)