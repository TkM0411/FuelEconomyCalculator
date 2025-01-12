locals {
    dynamic_tags = {
        "Created On Date" = formatdate("DD-MMM-YYYY", timeadd(timestamp(), "5h30m"))
        "Created At Time" = formatdate("hh:mm:ss", timeadd(timestamp(), "5h30m"))
    }
    common_tags = merge(var.static_tags, local.dynamic_tags)
}