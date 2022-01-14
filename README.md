# Mattermost-Tools
Mattermost tools developed with Mattermost API and mattermostdriver

## Component
- mattermost-auto-reply: Auto reply message on certain circumstances.

### mattermost-auto-reply
Config `reply_config` of `mm_conf.yaml` to use:
- message: The message to send.
- extend_message: Special message. If `extend_message` received, adjust next auto reply interval.
- interval: The interval when sending auto reply.
- max_interval: Set next auto reply interval to `max_interval` when receiving `extend_message`.
