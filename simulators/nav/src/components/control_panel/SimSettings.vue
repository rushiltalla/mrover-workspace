<!-- This file contains the SimSettings component which includes the Odom Format
     selector, the simulate localization checkbox, etc. -->

<!------------------------------------------- Template -------------------------------------------->
<template>
  <fieldset class="box">
    <legend>Settings</legend>
    <div class="sim-settings">
      <div class="field-size first setting">
        <p>Field Size (m):</p>
        <NumberInput
          :val.sync="fieldSizeIn"
          :min="5"
          :max="1000"
        />
      </div>

      <div class="odom-format setting">
        <p>Odom Format:</p>
        <RadioSelector
          :options="odomFormatOptions"
          :selection="odomFormat"
          @selected="selectOdomFormat"
        />
      </div>

      <div class="setting">
        <Checkbox
          :on="simulateLocalization"
          name="Simulate Localization"
          @clicked="flipSimulateLocalization(!simulateLocalization)"
        />
      </div>
      <div class="setting">
        <Checkbox
          :on="simulatePerception"
          name="Simulate Perception"
          @clicked="flipSimulatePerception(!simulatePerception)"
        />
      </div>
    </div>
  </fieldset>
</template>


<!-------------------------------------------- Script --------------------------------------------->
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Getter, Mutation } from 'vuex-class';
import { OdomFormat, RadioOption } from '../../utils/types';
import Checkbox from '../common/Checkbox.vue';
import NumberInput from '../common/NumberInput.vue';
import RadioSelector from '../common/RadioSelector.vue';

@Component({
  components: {
    Checkbox,
    NumberInput,
    RadioSelector
  }
})
export default class SimSettings extends Vue {
  /************************************************************************************************
   * Vuex Getters
   ************************************************************************************************/
  @Getter
  private readonly fieldSize!:number;

  @Getter
  private readonly odomFormat!:OdomFormat;

  @Getter
  private readonly simulateLocalization!:boolean;

  @Getter
  private readonly simulatePerception!:boolean;

  /************************************************************************************************
   * Vuex Mutations
   ************************************************************************************************/
  @Mutation
  private readonly setFieldSize!:(newFieldSize:number)=>void;

  @Mutation
  private readonly setOdomFormat!:(newOdomFormat:OdomFormat)=>void;

  @Mutation
  private readonly flipSimulateLocalization!:(onOff:boolean)=>void;

  @Mutation
  private readonly flipSimulatePerception!:(onOff:boolean)=>void;

  /************************************************************************************************
   * Private Members
   ************************************************************************************************/
  /* Odom format options */
  private readonly odomFormatOptions:RadioOption<OdomFormat>[] = [
    { value: OdomFormat.D,   name: 'D'   },
    { value: OdomFormat.DM,  name: 'DM'  },
    { value: OdomFormat.DMS, name: 'DMS' }
  ];

  /************************************************************************************************
   * Local Getters/Setters
   ************************************************************************************************/
  /* Displayed field size */
  private get fieldSizeIn():number {
    return this.fieldSize;
  }
  private set fieldSizeIn(newFieldSize:number) {
    this.setFieldSize(newFieldSize);
  }

  /************************************************************************************************
   * Private Methods
   ************************************************************************************************/
  /* Change current odom format selection. */
  private selectOdomFormat(selectedOdomFormat:OdomFormat):void {
    this.setOdomFormat(selectedOdomFormat);
  } /* selectOdomFormat() */
}
</script>


<!----------------------------------------- Scoped Style ------------------------------------------>
<style scoped>
.field-size p {
  margin-top: 4px;
}

.odom-format {
  display: flex;
  flex-wrap: wrap;
}

.odom-format p {
  margin-right: 3px;
}

p {
  display: inline-block;
  margin: auto;
}

.setting {
  margin-right: 10px;
}

.setting:last-child {
  margin-left: 0;
}

.sim-settings {
  display: flex;
  flex-wrap: wrap;
}
</style>
