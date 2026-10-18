int? _i(dynamic v) => (v as num?)?.toInt();
double? _d(dynamic v) => (v as num?)?.toDouble();

class Lead {
  Lead.fromJson(Map<String, dynamic> j)
      : id = j['id'] as int,
        name = j['name'] as String,
        phone = j['phone'] as String?,
        email = j['email'] as String?,
        status = j['status'] as String,
        priority = j['priority'] as String,
        budget = _i(j['budget']),
        preferredLocation = j['preferred_location'] as String?,
        propertyType = j['property_type'] as String?,
        downPayment = _i(j['down_payment']),
        monthlyInstallment = _i(j['monthly_installment']),
        purchaseTimeline = j['purchase_timeline'] as String?,
        consentStatus = j['consent_status'] as String,
        optedOut = j['opted_out'] as bool,
        conversationSummary = j['conversation_summary'] as String?,
        nextSteps = j['next_steps'] as String?;
  final int id;
  final String name;
  final String? phone, email, preferredLocation, propertyType, purchaseTimeline, conversationSummary, nextSteps;
  final String status, priority, consentStatus;
  final int? budget, downPayment, monthlyInstallment;
  final bool optedOut;
}

class Property {
  Property.fromJson(Map<String, dynamic> j)
      : id = j['id'] as int,
        code = j['code'] as String,
        title = j['title'] as String,
        propertyType = j['property_type'] as String,
        location = j['location'] as String,
        areaSqm = _d(j['area_sqm']),
        bedrooms = _i(j['bedrooms']),
        price = _i(j['price']),
        availability = j['availability'] as String,
        deliveryDate = j['delivery_date'] as String?,
        paymentPlan = j['payment_plan'] as String?,
        description = j['description'] as String?;
  final int id;
  final String code, title, propertyType, location, availability;
  final double? areaSqm;
  final int? bedrooms, price;
  final String? deliveryDate, paymentPlan, description;
}

class Activity {
  Activity.fromJson(Map<String, dynamic> j)
      : id = j['id'] as int,
        type = j['type'] as String,
        description = j['description'] as String,
        actor = j['actor'] as String,
        createdAt = DateTime.parse(j['created_at'] as String);
  final int id;
  final String type, description, actor;
  final DateTime createdAt;
}

class Booking {
  Booking.fromJson(Map<String, dynamic> j)
      : id = j['id'] as int,
        leadId = j['lead_id'] as int,
        leadName = j['lead_name'] as String,
        propertyId = j['property_id'] as int,
        propertyTitle = j['property_title'] as String,
        start = DateTime.parse(j['start'] as String),
        end = DateTime.parse(j['end'] as String),
        status = j['status'] as String,
        cancelReason = j['cancel_reason'] as String?;
  final int id, leadId, propertyId;
  final String leadName, propertyTitle, status;
  final DateTime start, end;
  final String? cancelReason;
}

class Slot {
  Slot.fromJson(Map<String, dynamic> j)
      : start = DateTime.parse(j['start'] as String),
        available = j['available'] as bool,
        reason = j['reason'] as String?;
  final DateTime start;
  final bool available;
  final String? reason;
}

class Handoff {
  Handoff.fromJson(Map<String, dynamic> j)
      : id = j['id'] as int,
        leadId = _i(j['lead_id']),
        leadName = j['lead_name'] as String?,
        category = j['category'] as String,
        reason = j['reason'] as String,
        status = j['status'] as String,
        assignedTo = j['assigned_to'] as String?,
        createdAt = DateTime.parse(j['created_at'] as String),
        events = ((j['events'] ?? const []) as List)
            .map((e) => Activity.fromJson(e as Map<String, dynamic>))
            .toList();
  final int id;
  final int? leadId;
  final String? leadName, assignedTo;
  final String category, reason, status;
  final DateTime createdAt;
  final List<Activity> events;
}

class Crm {
  Crm.fromJson(Map<String, dynamic> j)
      : lead = Lead.fromJson(j['lead'] as Map<String, dynamic>),
        qualificationComplete = j['qualification_complete'] as bool,
        missing = (j['missing_qualification'] as List).cast<String>(),
        activities = (j['activities'] as List).map((e) => Activity.fromJson(e as Map<String, dynamic>)).toList(),
        bookings = (j['bookings'] as List).map((e) => Booking.fromJson(e as Map<String, dynamic>)).toList(),
        handoffs = (j['handoffs'] as List).map((e) => Handoff.fromJson(e as Map<String, dynamic>)).toList(),
        openHandoffStatus = j['open_handoff_status'] as String?;
  final Lead lead;
  final bool qualificationComplete;
  final List<String> missing;
  final List<Activity> activities;
  final List<Booking> bookings;
  final List<Handoff> handoffs;
  final String? openHandoffStatus;
}

class PageResult<T> {
  PageResult(this.items, this.total);
  final List<T> items;
  final int total;
}
