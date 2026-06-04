# Add a node to ask for date or company if missing from initial query
# After receiving calirifcation determine if the user changed their query or just provided the missing info
# If new query redirect to filter extraction, if clarification, validate and proceed
# Add a node that explains why a query was failed
# Add a node for fuzzy filter valdiation
# Add routing from Query Decompositio to Clarification when the query fails due to lack of filters but I doubt we will ever get there cuz somehere else we get routed first