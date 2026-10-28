import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

final conversationLeadsProvider = FutureProvider.autoDispose<PageResult<Lead>>(
  (ref) => ref.watch(repoProvider).leads(limit: 200),
);

class ConversationScreen extends ConsumerStatefulWidget {
  const ConversationScreen({super.key});

  @override
  ConsumerState<ConversationScreen> createState() => _ConversationScreenState();
}

class _ConversationScreenState extends ConsumerState<ConversationScreen> {
  final _messageController = TextEditingController();
  int? _leadId;
  String _channel = 'whatsapp_sandbox';
  Conversation? _conversation;
  bool _busy = false;

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _startConversation() async {
    if (_leadId == null || _busy) return;
    setState(() => _busy = true);
    try {
      final conversation =
          await ref.read(repoProvider).openConversation(_leadId!, _channel);
      if (mounted) setState(() => _conversation = conversation);
    } catch (error) {
      if (mounted) snack(context, error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    final conversation = _conversation;
    if (text.isEmpty || conversation == null || _busy) return;
    setState(() => _busy = true);
    try {
      final updated =
          await ref.read(repoProvider).sendMessage(conversation.id, text);
      if (mounted) {
        setState(() {
          _conversation = updated;
          _messageController.clear();
        });
        ref.invalidate(conversationLeadsProvider);
      }
    } catch (error) {
      if (mounted) snack(context, error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      PageHeader(context.tr('nav_conversation')),
      Banner2(context.tr('chat_sandbox_note')),
      const SizedBox(height: 12),
      Expanded(
        child: AsyncBody<PageResult<Lead>>(
          value: ref.watch(conversationLeadsProvider),
          onRetry: () => ref.invalidate(conversationLeadsProvider),
          builder: (page) {
            if (page.items.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(context.tr('chat_no_leads')),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: () =>
                          ref.read(navIndexProvider.notifier).state = 2,
                      child: Text(context.tr('new_lead')),
                    ),
                  ],
                ),
              );
            }
            Lead? selectedLead;
            for (final lead in page.items) {
              if (lead.id == _leadId) {
                selectedLead = lead;
                break;
              }
            }
            final optedOut =
                _conversation?.lead.optedOut ?? selectedLead?.optedOut ?? false;
            return Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      flex: 2,
                      child: DropdownButtonFormField<int>(
                        initialValue:
                            page.items.any((lead) => lead.id == _leadId)
                                ? _leadId
                                : null,
                        isExpanded: true,
                        decoration: InputDecoration(
                            labelText: context.tr('chat_choose_lead')),
                        items: [
                          for (final lead in page.items)
                            DropdownMenuItem(
                              value: lead.id,
                              child: Text(
                                  '${lead.name} · ${context.tr(lead.status)}'),
                            ),
                        ],
                        onChanged: _busy
                            ? null
                            : (value) => setState(() {
                                  _leadId = value;
                                  _conversation = null;
                                }),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: _channel,
                        isExpanded: true,
                        decoration: InputDecoration(
                            labelText: context.tr('chat_channel')),
                        items: [
                          for (final channel in const [
                            'web_chat',
                            'whatsapp_sandbox',
                            'voice'
                          ])
                            DropdownMenuItem(
                              value: channel,
                              child: Text(context.tr(channel)),
                            ),
                        ],
                        onChanged: _busy
                            ? null
                            : (value) => setState(() {
                                  if (value == null) return;
                                  _channel = value;
                                  _conversation = null;
                                }),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: AlignmentDirectional.centerEnd,
                  child: OutlinedButton.icon(
                    onPressed: _busy || _leadId == null || optedOut
                        ? null
                        : _startConversation,
                    icon: const Icon(Icons.forum_outlined),
                    label: Text(context.tr('start_conversation')),
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: _conversation == null
                      ? Center(child: Text(context.tr('chat_not_started')))
                      : _MessageList(conversation: _conversation!),
                ),
                if (optedOut)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Banner2(context.tr('chat_opted_out')),
                  ),
                const SizedBox(height: 8),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        enabled: _conversation != null && !optedOut && !_busy,
                        maxLines: 3,
                        minLines: 1,
                        onSubmitted: (_) => _sendMessage(),
                        decoration: InputDecoration(
                          hintText: context.tr('message_hint'),
                          border: const OutlineInputBorder(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filled(
                      tooltip: context.tr('send_message'),
                      onPressed: _conversation == null || optedOut || _busy
                          ? null
                          : _sendMessage,
                      icon: _busy
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.send),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    ]);
  }
}

class _MessageList extends StatelessWidget {
  const _MessageList({required this.conversation});

  final Conversation conversation;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: conversation.messages.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final message = conversation.messages[index];
        final mine = message.role == 'user';
        return Align(
          alignment: mine
              ? AlignmentDirectional.centerEnd
              : AlignmentDirectional.centerStart,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Card(
              color: mine
                  ? Theme.of(context).colorScheme.primaryContainer
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(message.text),
                    if (message.citations.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(context.tr('chat_citations'),
                          style: Theme.of(context).textTheme.labelMedium),
                      for (final citation in message.citations)
                        Text('${citation.source}: ${citation.text}',
                            style: Theme.of(context).textTheme.bodySmall),
                    ],
                    if (message.moduleGaps.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        '${context.tr('chat_module_gaps')}: ${message.moduleGaps.join(', ')}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
