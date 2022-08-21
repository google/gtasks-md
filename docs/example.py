from pandoc import types

# pyright still has some way to go
Decimal = types.Decimal  # type: ignore
Header = types.Header  # type: ignore
Meta = types.Meta  # type: ignore
OrderedList = types.OrderedList  # type: ignore
Pandoc = types.Pandoc  # type: ignore
Para = types.Para  # type: ignore
Period = types.Period  # type: ignore
Plain = types.Plain  # type: ignore
SoftBreak = types.SoftBreak  # type: ignore
Space = types.Space  # type: ignore
Str = types.Str  # type: ignore

Pandoc(
    Meta({}),
    [
        Header(1, ("todo", [], []), [Str("TODO")]),
        Header(2, ("tasklist-1", [], []), [Str("Tasklist"), Space(), Str("1")]),
        OrderedList(
            (1, Decimal(), Period()),
            [
                [
                    Plain([Str("☐"), Space(), Str("Task"), Space(), Str("1")]),
                    OrderedList(
                        (1, Decimal(), Period()),
                        [
                            [
                                Plain(
                                    [
                                        Str("☐"),
                                        Space(),
                                        Str("Subtask"),
                                        Space(),
                                        Str("1"),
                                    ]
                                )
                            ],
                            [
                                Plain(
                                    [
                                        Str("☒"),
                                        Space(),
                                        Str("Subtask"),
                                        Space(),
                                        Str("2"),
                                    ]
                                )
                            ],
                        ],
                    ),
                ],
                [
                    Plain([Str("☒"), Space(), Str("Task"), Space(), Str("2")]),
                    OrderedList(
                        (1, Decimal(), Period()),
                        [
                            [
                                Plain(
                                    [
                                        Str("☒"),
                                        Space(),
                                        Str("Subtask"),
                                        Space(),
                                        Str("1"),
                                    ]
                                )
                            ]
                        ],
                    ),
                ],
            ],
        ),
        Header(2, ("tasklist-2", [], []), [Str("Tasklist"), Space(), Str("2")]),
        OrderedList(
            (1, Decimal(), Period()),
            [
                [
                    Para([Str("☐"), Space(), Str("Task"), Space(), Str("1")]),
                    Para(
                        [Str("Task"), Space(), Str("1"), Space(), Str("description.")]
                    ),
                    OrderedList(
                        (1, Decimal(), Period()),
                        [
                            [
                                Para(
                                    [
                                        Str("☐"),
                                        Space(),
                                        Str("Subtask"),
                                        Space(),
                                        Str("1"),
                                    ]
                                ),
                                Para(
                                    [
                                        Str("Subtask"),
                                        Space(),
                                        Str("1"),
                                        Space(),
                                        Str("description."),
                                    ]
                                ),
                            ],
                            [
                                Para(
                                    [
                                        Str("☐"),
                                        Space(),
                                        Str("Subtask"),
                                        Space(),
                                        Str("2"),
                                    ]
                                ),
                                Para(
                                    [
                                        Str("Lorem"),
                                        Space(),
                                        Str("ipsum"),
                                        Space(),
                                        Str("dolor"),
                                        Space(),
                                        Str("sit"),
                                        Space(),
                                        Str("amet,"),
                                        Space(),
                                        Str("consectetur"),
                                        Space(),
                                        Str("adipiscing"),
                                        Space(),
                                        Str("elit."),
                                        Space(),
                                        Str("Mauris"),
                                        Space(),
                                        Str("mauris"),
                                        SoftBreak(),
                                        Str("mi,"),
                                        Space(),
                                        Str("luctus"),
                                        Space(),
                                        Str("non"),
                                        Space(),
                                        Str("vulputate"),
                                        Space(),
                                        Str("quis,"),
                                        Space(),
                                        Str("gravida"),
                                        Space(),
                                        Str("eu"),
                                        Space(),
                                        Str("dolor."),
                                    ]
                                ),
                            ],
                        ],
                    ),
                ]
            ],
        ),
    ],
)
