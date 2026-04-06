/**
 * Everlight Broker OS -- Gmail Label & Filter Setup
 *
 * HOW TO USE:
 * 1. Go to https://script.google.com
 * 2. Click "+ New project"
 * 3. Delete the default code, paste this entire file
 * 4. Click Run (select setupBrokerOS from dropdown)
 * 5. Authorize when prompted (one time)
 * 6. Check the Execution Log -- done!
 *
 * IMPORTANT: Enable Gmail API first:
 *   Click "Services" (+) on the left sidebar > search "Gmail API" > Add
 */

function setupBrokerOS() {
  // -- Step 1: Create Labels --
  var labels = [
    "Everlight",
    "Everlight/Broker_OS",
    "Everlight/Broker_OS/Sage_Inbox",
    "Everlight/Broker_OS/Seller_Replies",
    "Everlight/Broker_OS/Buyer_Leads"
  ];

  var createdLabels = {};

  labels.forEach(function(labelName) {
    try {
      var label = Gmail.Users.Labels.create({
        name: labelName,
        labelListVisibility: "labelShow",
        messageListVisibility: "show"
      }, "me");
      createdLabels[labelName] = label.id;
      Logger.log("Created label: " + labelName + " (ID: " + label.id + ")");
    } catch (e) {
      if (e.message.indexOf("already exists") > -1) {
        // Find existing label ID
        var allLabels = Gmail.Users.Labels.list("me").labels;
        for (var i = 0; i < allLabels.length; i++) {
          if (allLabels[i].name === labelName) {
            createdLabels[labelName] = allLabels[i].id;
            break;
          }
        }
        Logger.log("Label already exists: " + labelName);
      } else {
        Logger.log("Error creating " + labelName + ": " + e.message);
      }
    }
  });

  // -- Step 2: Create Filters --
  var sageId = createdLabels["Everlight/Broker_OS/Sage_Inbox"];
  var sellerId = createdLabels["Everlight/Broker_OS/Seller_Replies"];
  var buyerId = createdLabels["Everlight/Broker_OS/Buyer_Leads"];

  // Filter 1: All sage@ emails -> Sage_Inbox + Star
  if (sageId) {
    try {
      Gmail.Users.Settings.Filters.create({
        criteria: { to: "sage@everlightventures.io" },
        action: {
          addLabelIds: [sageId, "STARRED"],
          removeLabelIds: []
        }
      }, "me");
      Logger.log("Filter created: to:sage@ -> Sage_Inbox + Star");
    } catch (e) {
      Logger.log("Filter may already exist (sage): " + e.message);
    }
  }

  // Filter 2: Seller replies (partnership keywords) -> Seller_Replies
  if (sellerId) {
    try {
      Gmail.Users.Settings.Filters.create({
        criteria: {
          to: "sage@everlightventures.io",
          subject: "partnership OR listing OR integration OR collaborate"
        },
        action: {
          addLabelIds: [sellerId],
          removeLabelIds: []
        }
      }, "me");
      Logger.log("Filter created: sage + partnership keywords -> Seller_Replies");
    } catch (e) {
      Logger.log("Filter may already exist (seller): " + e.message);
    }
  }

  // Filter 3: Buyer lead notifications -> Buyer_Leads
  if (buyerId) {
    try {
      Gmail.Users.Settings.Filters.create({
        criteria: {
          to: "sage@everlightventures.io",
          subject: "looking for OR need a tool OR recommend OR solution"
        },
        action: {
          addLabelIds: [buyerId],
          removeLabelIds: []
        }
      }, "me");
      Logger.log("Filter created: sage + buyer keywords -> Buyer_Leads");
    } catch (e) {
      Logger.log("Filter may already exist (buyer): " + e.message);
    }
  }

  Logger.log("");
  Logger.log("Broker OS Gmail setup complete!");
  Logger.log("Labels: Everlight/Broker_OS/Sage_Inbox, Seller_Replies, Buyer_Leads");
  Logger.log("Filters: 3 auto-label rules active");
}
