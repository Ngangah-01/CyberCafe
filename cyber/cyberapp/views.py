from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Student, Payment, UsageSession
from .forms import StudentForm, PaymentForm
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_daraja.mpesa.core import MpesaClient
import json
from decimal import Decimal


# Create your views here.

@login_required
def home(request):
    #optimize queries with prefetch_related to reduce DB hits/N+1 problem
    students = Student.objects.prefetch_related('usagesession_set').all()
    
    for student in students:
        sessions = student.usagesession_set.all()
        
        # Check for active session (is_active=True and no end_time)
        active_session = next((s for s in sessions if s.is_active and not s.end_time), None)
        
        if active_session:
            student.active_start_time = active_session.start_time
            student.has_active_session = True
            student.duration_in_hours = active_session.duration_in_hours()
        else:
            student.active_start_time = None
            student.has_active_session = False
            student.duration_in_hours = "N/a"
        
        # Total hours from completed sessions only (end_time not null)
        # completed_sessions = [s for s in sessions if s.end_time]
        # total_hours = sum(s.duration_in_hours() for s in completed_sessions)
        # student.total_hours = round(total_hours, 1)  # 1 decimal for display
    
    context = {
        'students': students,
        'now': timezone.now(),  # For header date if needed
    }
    return render(request, 'home.html', context)

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

def add_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('payment_list')
    else:
        form = PaymentForm()
    return render(request, 'add_payment.html', {'form': form})

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
def end_session(request, idnumber):
    student = get_object_or_404(Student, idnumber=idnumber)
    session = UsageSession.objects.filter(
        student=student,
        is_active=True,
        end_time__isnull=True
    ).first()
    
    if session:
        if request.method == 'POST':
            # Handle AJAX or regular POST
            session.end_time = timezone.now()
            session.is_active = False
            session.save()
            amount_due = session.total_amount()
            
            messages.success(request, f"Session ended for {student.firstname} {student.lastname}. Amount due: {amount_due} KSH.")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # AJAX
                return JsonResponse({'status': 'success', 'amount': amount_due})
            else:
                next_page = request.GET.get('next', 'active_sessions')  # Fallback to active_sessions
                return redirect(next_page)
        else:
            # For regular GET, perhaps render confirmation – but skip for now
            pass
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'No active session'})
        messages.error(request, "No active session found.")
        return redirect('active_sessions')
    
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

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """
    Endpoint to handle M-Pesa STK Push callbacks.
    M-Pesa POSTs JSON here after user enters PIN (success/fail).
    Returns {'ResultCode': 0, 'ResultDesc': 'Accepted'} to acknowledge.
    """
    try:
        # Parse the incoming JSON body from M-Pesa
        body = json.loads(request.body)
        callback_data = body.get('Body', {}).get('stkCallback', {})

        # Extract key fields
        checkout_request_id = callback_data.get('CheckoutRequestID')
        result_code = callback_data.get('ResultCode')

        if result_code == 0:  # Payment successful
            # Parse metadata for details
            metadata = callback_data.get('CallbackMetadata', {}).get('Item', [])
            amount = next((item['Value'] for item in metadata if item['Name'] == 'Amount'), None)
            receipt_number = next((item['Value'] for item in metadata if item['Name'] == 'MpesaReceiptNumber'), None)
            phone_number = next((item['Value'] for item in metadata if item['Name'] == 'PhoneNumber'), None)
            transaction_time = next((item['Value'] for item in metadata if item['Name'] == 'TransactionCompletedTime'), None)

            # TODO: Update your database here
            # Example: Find session by checkout_request_id (store it during STK initiation)
            # from .models import Session
            # session = Session.objects.get(checkout_request_id=checkout_request_id)
            # session.payment_status = 'paid'
            # session.mpesa_receipt = receipt_number
            # session.amount_paid = amount
            # session.save()

            # Log or notify (e.g., send email/SMS)
            print(f"Payment success: {amount} KSH from {phone_number}, Receipt: {receipt_number}, Time: {transaction_time}")

        else:  # Payment failed (e.g., cancelled by user)
            result_desc = callback_data.get('ResultDesc', 'Unknown failure')
            
            # TODO: Update DB to 'failed'
            # session = Session.objects.get(checkout_request_id=checkout_request_id)
            # session.payment_status = 'failed'
            # session.save()

            print(f"Payment failed for {checkout_request_id}: {result_desc}")

        # Always acknowledge to M-Pesa (they require this format)
        return JsonResponse({
            'ResultCode': 0,
            'ResultDesc': 'Accepted'
        })

    except json.JSONDecodeError:
        # Invalid JSON from M-Pesa (rare)
        return JsonResponse({
            'ResultCode': 1,
            'ResultDesc': 'Invalid JSON'
        }, status=400)

    except Exception as e:
        # Catch-all for errors
        print(f"Callback error: {e}")
        return JsonResponse({
            'ResultCode': 1,
            'ResultDesc': 'Processing failed'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def sendSTK(request):
    session_id = request.POST.get('session_id')
    phone_input = request.POST.get('phone_number')
    if not session_id:
        return JsonResponse({'error': 'Session ID required'}, status=400)

    try:
        session = UsageSession.objects.get(id=session_id)
        student = session.student  # Assuming Session has a student foreign key
        phone = phone_input if phone_input else student.phonenumber# Assume field exists (e.g., '0712345678')
        
        if not phone:
            return JsonResponse({'error': 'Phone number required'}, status=400)

        # Format phone to international: 25471xxxxxxxx
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('7'):
            phone = '2547' + phone[1:]
        # Validate: 12 digits starting with 2547
        if len(phone) != 12 or not phone.startswith('2547'):
            return JsonResponse({'error': 'Invalid phone format'}, status=400)

        # Placeholder amount; replace with your logic (e.g., based on session duration)
        amount = Decimal('1000.00')
        
        account_reference = f'Session-{session.id}-{student.idnumber}'  # Assuming idnumber field
        transaction_desc = f'Payment for session {session.id} on {session.start_time.date()}'
        callback_url = request.build_absolute_uri('/mpesa/callback/')  # Full public HTTPS URL

        cl = MpesaClient()
        response = cl.stk_push(
            phone_number=phone,
            amount=str(amount),  # Must be string for API
            account_reference=account_reference,
            transaction_desc=transaction_desc,
            callback_url=callback_url
        )

        if response.get('ResponseCode') == '0':
            # Update session (add fields like payment_status, checkout_request_id to your model)
            session.payment_status = 'pending'
            session.checkout_request_id = response.get('CheckoutRequestID')
            session.save()
            
            return JsonResponse({
                'success': True,
                'message': 'STK push sent! Check phone for prompt.',
                'checkout_request_id': response.get('CheckoutRequestID')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': response.get('errorMessage', 'STK push failed')
            }, status=400)

    except UsageSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)