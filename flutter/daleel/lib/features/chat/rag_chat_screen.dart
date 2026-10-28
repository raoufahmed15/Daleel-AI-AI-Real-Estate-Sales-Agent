import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

class _ChatEntry {
  const _ChatEntry({
    required this.isUser,
    required this.text,
    this.sources = const [],
    this.handoffReason,
  });

  final bool isUser;
  final String text;
  final List<RagSource> sources;
  final String? handoffReason;
}

class RagChatScreen extends ConsumerStatefulWidget {
  const RagChatScreen({super.key});

  @override
  ConsumerState<RagChatScreen> createState() => _RagChatScreenState();
}

class _RagChatScreenState extends ConsumerState<RagChatScreen> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  late String _sessionId;
  late List<_ChatEntry> _messages;
  bool _busy = false;

  String get _greeting {
    final isArabic = Localizations.localeOf(context).languageCode == 'ar';
    return isArabic
        ? 'أهلًا بك! أنا مساعد دليل العقاري. اسألني عن الوحدات والأسعار والتوافر وخطط السداد، وسأجيبك من المصادر المعتمدة.'
        : 'Welcome! I am Daleel’s real-estate assistant. Ask about units, prices, availability, or payment plans. I answer using approved sources.';
  }

  @override
  void initState() {
    super.initState();
    _sessionId = _newSessionId();
    _messages = const [];
  }

  String _newSessionId() =>
      '${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(0x7fffffff).toRadixString(16)}';

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _startNewChat() {
    if (_busy) return;
    setState(() {
      _sessionId = _newSessionId();
      _messages = [];
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _busy) return;

    _messageController.clear();
    setState(() {
      _busy = true;
      _messages = [..._messages, _ChatEntry(isUser: true, text: text)];
    });
    _scrollToBottom();

    try {
      final answer = await ref.read(repoProvider).askRag(text, _sessionId);
      if (!mounted) return;
      setState(() {
        _messages = [
          ..._messages,
          _ChatEntry(
            isUser: false,
            text: answer.reply,
            sources: answer.sources,
            handoffReason: answer.reason,
          ),
        ];
      });
      _scrollToBottom();
    } catch (error) {
      if (mounted) snack(context, error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isArabic = Localizations.localeOf(context).languageCode == 'ar';
    final messages = _messages.isEmpty
        ? [_ChatEntry(isUser: false, text: _greeting)]
        : _messages;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: PageHeader(context.tr('nav_chat'))),
            IconButton(
              tooltip: context.tr('new_chat'),
              onPressed: _busy ? null : _startNewChat,
              icon: const Icon(Icons.add_comment_outlined),
            ),
          ],
        ),
        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: messages.length + (_busy ? 1 : 0),
            itemBuilder: (context, index) {
              if (_busy && index == messages.length) {
                return Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                  ),
                );
              }
              return _MessageBubble(entry: messages[index]);
            },
          ),
        ),
        const SizedBox(height: 8),
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                enabled: !_busy,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _sendMessage(),
                decoration: InputDecoration(
                  hintText:
                      isArabic ? 'اكتب سؤالك هنا...' : 'Ask a question...',
                  border: const OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              tooltip: context.tr('send_message'),
              onPressed: _busy ? null : _sendMessage,
              icon: const Icon(Icons.send),
            ),
          ],
        ),
      ],
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.entry});

  final _ChatEntry entry;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Align(
      alignment: entry.isUser
          ? AlignmentDirectional.centerEnd
          : AlignmentDirectional.centerStart,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: Card(
          color: entry.isUser
              ? colorScheme.primaryContainer
              : colorScheme.surfaceContainerHighest,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SelectableText(entry.text),
                if (entry.handoffReason != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    '${context.tr('human_handoff')}: ${context.tr(entry.handoffReason!)}',
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ],
                if (entry.sources.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    context.tr('chat_citations'),
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                  for (final source in entry.sources)
                    Text(
                      [
                        source.title.isEmpty ? source.docId : source.title,
                        if (source.version.isNotEmpty) source.version,
                        if (source.issueDate.isNotEmpty) source.issueDate,
                      ].join(' · '),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
