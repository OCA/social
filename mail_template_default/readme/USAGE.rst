To use this module, you need to first create **Mail Template Rules**

| Rules are executed in a specific order based on the amount of information entered into the rule.
| The first rule to meet all the conditions is taken
| Mail Template Rules are sorted base on 4 fields in following hierarchy:
| Context Flag -> Company -> Filter -> Sequence
|
|

.. list-table:: The table shows hypothetical order of rules
   :widths: 20 20 20 20
   :header-rows: 1

   * - Context Flag
     - Company
     - Filter
     - Sequence
   * - x
     - x
     - x
     - 1
   * - x
     - x
     - x
     - 2
   * - x
     -
     -
     - 2
   * -
     - x
     - x
     - 1
   * -
     - x
     -
     - 1
   * -
     -
     - x
     - 2
   * -
     -
     - x
     - 3
   * -
     -
     -
     - 1
