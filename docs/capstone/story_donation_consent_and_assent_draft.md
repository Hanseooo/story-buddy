# Story Donation Consent and Assent — Draft for Ethics Review

> **DRAFT — DO NOT ADMINISTER.** This material requires adviser and institutional ethics approval. Replace
> bracketed administrative fields before approval. This is not legal advice.

## A. Parent/Guardian informed-consent draft

### Study and invitation

Your child is invited to donate a story to the StoryBuddy capstone study conducted by [researcher/institution].
Participation is voluntary. Choosing not to participate will not affect grades, school services or the
child's relationship with the school.

### What will happen

If you and your child agree, the research team will:

1. receive the story without the child's name or direct identifying information;
2. manually remove or replace any personal information found in the story;
3. use an AI system to generate character-reference and story-scene images;
4. ask trained researchers to compare and label those images;
5. use the de-identified story, images and labels to train and evaluate an AI character-consistency model;
6. report combined research results without identifying the child.

The story and generated images may be processed by the third-party computing services named in the approved
study protocol. They will receive only the de-identified material required for the task.

### Risks and safeguards

Possible risks include accidental personal information in the story, generated images that do not match the
story, and the privacy risks inherent in online processing. The team manually redacts donated stories before
generation, stores research images privately, uses short-lived access links and limits access to authorized
researchers. No raw submission or identity ledger is placed in the software repository or model dataset.

### Benefits and payment

There may be no direct benefit to your child. The study may improve tools for illustrating children's stories.
[State compensation or explicitly state that none is offered.]

### Withdrawal and retention

The team will issue a random receipt code. Keep this code; it is how a donation can be located without storing
the child's name in the research dataset. You or your child may withdraw the donation until [dataset-freeze
date/event] by contacting [approved contact] and providing the code. Before that cutoff, the sanitized story
and its derived images, labels and dataset records will be excluded and deleted under the approved retention
procedure.

After model training begins, the team can exclude the donation from future training and evaluation, but it
may not be technically possible to remove one donation's influence from a model already trained. State the
approved final retention/deletion schedule here: [schedule].

### Questions and contacts

Study questions: [researcher/adviser contact]. Rights or complaints: [ethics-office contact]. Do not place
these contact details in the public dataset or repository.

### Consent

- I have read or had this information explained to me.
- I had an opportunity to ask questions.
- I understand the story and generated images may be used for AI model training and evaluation.
- I understand the withdrawal cutoff and the limitation after training begins.
- I voluntarily permit my child to participate.

Guardian name/signature: ____________________ Date: __________

Child receipt code (issued by researcher): ____________________

Researcher/witness: _________________________ Date: __________

## B. Child assent draft

### Would you like to share your story with our study?

We are studying a tool that turns stories into picture books. If you say yes:

- we will remove names and other details that could identify you;
- a computer program will make pictures from your story;
- researchers will compare and label the pictures;
- the story, pictures and labels may help train and test an AI model;
- reports will not use your name.

You do not have to join. Saying no will not affect your grades or school activities. You may ask questions at
any time. You may ask us to stop using your story before the dataset is locked by giving us your receipt code.
After model training starts, we may be unable to remove what an already-trained model learned, but we can stop
using your story in later training and tests.

Please tick one:

- [ ] **Yes**, I want to share my story for this study.
- [ ] **No**, I do not want to share my story for this study.

Child name/signature as required by the approved process: ____________________

Date: __________  Receipt code: ____________________

Person explaining the study: ____________________

## C. Restricted receipt ledger template

Keep this outside the repository and research database in the ethics-approved restricted location.

| Receipt code | Approved participant/contact record | Guardian consent date | Child assent date | Withdrawal state/date |
|---|---|---|---|---|

The de-identified intake and all derived artifacts carry only the receipt-derived `donation_id`, never the
participant/contact record.

## D. Approval checklist

- [ ] Adviser approved wording.
- [ ] HCDC ethics reviewer approved wording and retention schedule.
- [ ] Participating school approved the contact and administration process.
- [ ] Required guardian-consent and child-assent process confirmed.
- [ ] Third-party processors and retention period named accurately.
- [ ] Withdrawal cutoff is a calendar date or unambiguous event.
- [ ] Filipino/Tagalog translation reviewed for age appropriateness if administered.
- [ ] Blank administrative placeholders removed before administration.
